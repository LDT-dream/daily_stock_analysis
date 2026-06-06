# -*- coding: utf-8 -*-
"""
韩国股票数据源 - 基于 FinanceDataReader

支持 KRX (KOSPI) 和 KOSDAQ 市场的韩国股票数据获取。
数据来源：FinanceDataReader (https://github.com/FinanceData/FinanceDataReader)

功能：
- 实时行情获取
- 历史日线数据
- 股票名称解析
- 基本面数据（市值、行业等）
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import pandas as pd

from .base import BaseFetcher
from .realtime_types import UnifiedRealtimeQuote

logger = logging.getLogger(__name__)


def _is_kr_code(stock_code: str) -> bool:
    """判断代码是否为韩国股票（.KS/.KQ 后缀）。"""
    code = (stock_code or "").strip().upper()
    return code.endswith('.KS') or code.endswith('.KQ')


def _extract_kr_symbol(stock_code: str) -> str:
    """从韩国股票代码中提取纯数字代码（去掉 .KS/.KQ 后缀）。"""
    code = (stock_code or "").strip().upper()
    if code.endswith('.KS') or code.endswith('.KQ'):
        return code[:-3]
    return code


class KoreaFinanceFetcher(BaseFetcher):
    """
    韩国股票数据源 - 基于 FinanceDataReader

    优先级：6（低于 YfinanceFetcher 的 4，作为补充数据源）
    """

    name = "KoreaFinanceFetcher"
    priority = 6

    def __init__(self):
        super().__init__()
        self._stock_list_cache: Optional[pd.DataFrame] = None
        self._stock_list_cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从 FinanceDataReader 获取原始数据。"""
        if not _is_kr_code(stock_code):
            return pd.DataFrame()

        symbol = _extract_kr_symbol(stock_code)
        try:
            import FinanceDataReader as fdr
            # 转换日期格式
            start = start_date.replace('-', '')
            end = end_date.replace('-', '')
            df = fdr.DataReader(symbol, start, end)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.warning(f"[韩国数据] 获取原始数据失败 {stock_code}: {e}")
            return pd.DataFrame()

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """标准化数据列名。"""
        if df.empty:
            return df

        # FinanceDataReader 返回的列名: Open, High, Low, Close, Volume, Change
        column_mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Change': 'pct_chg',
            'Amount': 'amount',
        }

        # 只重命名存在的列
        rename_map = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=rename_map)

        # 添加缺失的列
        if 'amount' not in df.columns:
            df['amount'] = 0.0
        if 'pct_chg' not in df.columns:
            df['pct_chg'] = 0.0

        return df

    def _get_stock_list(self) -> pd.DataFrame:
        """获取韩国股票列表（带缓存）。"""
        now = datetime.now()
        if (self._stock_list_cache is not None and
                self._stock_list_cache_time is not None and
                now - self._stock_list_cache_time < self._cache_ttl):
            return self._stock_list_cache

        try:
            import FinanceDataReader as fdr
            df = fdr.StockListing('KRX')
            self._stock_list_cache = df
            self._stock_list_cache_time = now
            logger.info(f"[韩国数据] 加载股票列表: {len(df)} 只")
            return df
        except Exception as e:
            logger.warning(f"[韩国数据] 获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """获取韩国股票名称。"""
        if not _is_kr_code(stock_code):
            return None

        symbol = _extract_kr_symbol(stock_code)
        try:
            df_list = self._get_stock_list()
            if df_list.empty:
                return None

            row = df_list[df_list['Code'] == symbol]
            if not row.empty:
                name = row.iloc[0]['Name']
                # 韩文名称，返回韩文
                return str(name) if pd.notna(name) else None
        except Exception as e:
            logger.debug(f"[韩国数据] 获取股票名称失败 {stock_code}: {e}")

        return None

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """获取韩国股票实时行情。"""
        if not _is_kr_code(stock_code):
            return None

        symbol = _extract_kr_symbol(stock_code)
        try:
            import FinanceDataReader as fdr

            # 获取最近几天的数据来计算涨跌幅
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

            df = fdr.DataReader(symbol, start_date, end_date)
            if df.empty:
                logger.warning(f"[韩国数据] {stock_code} 无数据")
                return None

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            price = float(latest['Close'])
            prev_close = float(prev['Close'])
            change_amount = price - prev_close
            change_pct = (change_amount / prev_close * 100) if prev_close > 0 else 0

            # 获取股票名称
            stock_name = self.get_stock_name(stock_code)

            # 获取市值信息
            market_cap = None
            try:
                df_list = self._get_stock_list()
                if not df_list.empty:
                    row = df_list[df_list['Code'] == symbol]
                    if not row.empty and 'Marcap' in row.columns:
                        market_cap = float(row.iloc[0]['Marcap'])
            except Exception:
                pass

            return UnifiedRealtimeQuote(
                code=stock_code,
                name=stock_name or stock_code,
                price=price,
                change_pct=change_pct,
                change_amount=change_amount,
                volume=int(latest['Volume']),
                amount=float(latest.get('Amount', 0)) if 'Amount' in latest.index else None,
                open_price=float(latest['Open']),
                high=float(latest['High']),
                low=float(latest['Low']),
                pre_close=prev_close,
                total_mv=market_cap,
                source="FinanceDataReader",
                fetched_at=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.warning(f"[韩国数据] 获取实时行情失败 {stock_code}: {e}")
            return None

    def get_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30,
    ) -> Optional[pd.DataFrame]:
        """获取韩国股票日线数据。"""
        if not _is_kr_code(stock_code):
            return None

        symbol = _extract_kr_symbol(stock_code)
        try:
            import FinanceDataReader as fdr

            if start_date is None:
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')

            # 转换日期格式（如果需要）
            start_date = start_date.replace('-', '')
            end_date = end_date.replace('-', '')

            df = fdr.DataReader(symbol, start_date, end_date)
            if df.empty:
                return None

            # 统一列名（与 yfinance 格式一致）
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Change': 'change',
            })

            # 添加股票代码列
            df['code'] = stock_code

            return df

        except Exception as e:
            logger.warning(f"[韩国数据] 获取日线数据失败 {stock_code}: {e}")
            return None

    def get_market_overview(self) -> Optional[Dict[str, Any]]:
        """获取韩国市场概览（KOSPI/KOSDAQ 指数）。"""
        try:
            import FinanceDataReader as fdr

            # 获取 KOSPI 指数
            kospi = fdr.DataReader('KS11', (datetime.now() - timedelta(days=7)).strftime('%Y%m%d'))
            kosdaq = fdr.DataReader('KQ11', (datetime.now() - timedelta(days=7)).strftime('%Y%m%d'))

            result = {}

            if not kospi.empty:
                latest_kospi = kospi.iloc[-1]
                prev_kospi = kospi.iloc[-2] if len(kospi) > 1 else latest_kospi
                result['kospi'] = {
                    'price': float(latest_kospi['Close']),
                    'change_pct': (float(latest_kospi['Close']) - float(prev_kospi['Close'])) / float(prev_kospi['Close']) * 100,
                }

            if not kosdaq.empty:
                latest_kosdaq = kosdaq.iloc[-1]
                prev_kosdaq = kosdaq.iloc[-2] if len(kosdaq) > 1 else latest_kosdaq
                result['kosdaq'] = {
                    'price': float(latest_kosdaq['Close']),
                    'change_pct': (float(latest_kosdaq['Close']) - float(prev_kosdaq['Close'])) / float(prev_kosdaq['Close']) * 100,
                }

            return result

        except Exception as e:
            logger.warning(f"[韩国数据] 获取市场概览失败: {e}")
            return None

    def get_sector_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取韩国股票行业信息。"""
        if not _is_kr_code(stock_code):
            return None

        symbol = _extract_kr_symbol(stock_code)
        try:
            df_list = self._get_stock_list()
            if df_list.empty:
                return None

            row = df_list[df_list['Code'] == symbol]
            if row.empty:
                return None

            row = row.iloc[0]
            return {
                'market': row.get('Market', ''),
                'sector': row.get('Dept', ''),  # Dept is like sector/industry
                'market_cap': float(row.get('Marcap', 0)) if pd.notna(row.get('Marcap')) else None,
                'shares_outstanding': int(row.get('Stocks', 0)) if pd.notna(row.get('Stocks')) else None,
            }

        except Exception as e:
            logger.debug(f"[韩国数据] 获取行业信息失败 {stock_code}: {e}")
            return None
