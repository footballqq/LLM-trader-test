# // codex: 2025-09-16 支持 Wind 基金净值字段拆分
from abc import ABC, abstractmethod
import logging
from typing import Iterable, List, Sequence

import pandas as pd
from WindPy import w


class DataProvider(ABC):
    """
    Abstract base class for data providers.
    Defines a common interface for fetching financial data.
    """

    @abstractmethod
    def get_data(self, codes: Iterable[str], start_date, end_date) -> pd.DataFrame:
        """
        Fetches data for given codes over a specified period.

        Args:
            codes: Iterable of ticker symbols.
            start_date: Start date for the data (str or pd.Timestamp).
            end_date: End date for the data (str or pd.Timestamp).

        Returns:
            pd.DataFrame: A DataFrame with a DatetimeIndex and columns for each code.
        """


class WindDataProvider(DataProvider):
    """
    A data provider that fetches data from the Wind API.
    """

    FUND_SUFFIX = ".OF"

    def __init__(self) -> None:
        """Initializes the WindDataProvider and connects to the Wind API."""
        self._connect()

    def _connect(self) -> None:
        """Connects to the Wind API if not already connected."""
        if not w.isconnected():
            logging.info("Connecting to Wind API...")
            w.start()
        else:
            logging.info("Already connected to Wind API.")

    def get_data(self, codes: Iterable[str], start_date, end_date) -> pd.DataFrame | None:
        codes_list: List[str] = list(codes)
        if not codes_list:
            logging.warning("No codes provided to WindDataProvider.get_data.")
            return pd.DataFrame()

        if isinstance(start_date, pd.Timestamp):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, pd.Timestamp):
            end_date = end_date.strftime("%Y-%m-%d")

        logging.info(
            "Requesting Wind data for %s from %s to %s",
            codes_list,
            start_date,
            end_date,
        )

        fund_codes = [code for code in codes_list if code.upper().endswith(self.FUND_SUFFIX)]
        other_codes = [code for code in codes_list if not code.upper().endswith(self.FUND_SUFFIX)]

        frames = []
        for group_name, group_codes, field, options in (
            ("fund", fund_codes, "NAV_adj", "PriceAdj=B"),
            ("non_fund", other_codes, "close", "PriceAdj=F"),
        ):
            if not group_codes:
                continue
            frame = self._fetch_group(
                group_name=group_name,
                codes=group_codes,
                field=field,
                start_date=start_date,
                end_date=end_date,
                options=options,
            )
            if frame is None:
                return None
            frames.append(frame)

        if not frames:
            logging.warning("Wind returned no data for codes %s", codes_list)
            return pd.DataFrame()

        combined = pd.concat(frames, axis=1)

        ordered_columns: List[str] = []
        normalized_map = {column.upper(): column for column in combined.columns}
        missing_codes: List[str] = []
        for code in codes_list:
            normalized = code.upper()
            if normalized in normalized_map:
                ordered_columns.append(normalized_map[normalized])
            else:
                missing_codes.append(code)
        if missing_codes:
            logging.warning("Wind data missing columns for codes: %s", missing_codes)

        if ordered_columns:
            combined = combined.loc[:, ordered_columns]

        logging.info("Wind data head:\n%s\n", combined.head())
        return combined

    def _fetch_group(
        self,
        *,
        group_name: str,
        codes: Sequence[str],
        field: str,
        start_date: str,
        end_date: str,
        options: str,
    ) -> pd.DataFrame | None:
        logging.info(
            "Fetching %s series from Wind with field=%s and options=%s",
            group_name,
            field,
            options,
        )
        result = w.wsd(codes, field, start_date, end_date, options)

        if result.ErrorCode != 0:
            logging.error(
                "Wind API Error for %s codes %s. ErrorCode: %s, Message: %s",
                group_name,
                codes,
                result.ErrorCode,
                result.Data,
            )
            return None

        frame = pd.DataFrame(result.Data, index=result.Codes, columns=result.Times).T
        frame.index = pd.to_datetime(frame.index)
        return frame

    def __del__(self) -> None:
        """Destructor to stop the Wind API connection."""
        try:
            if w.isconnected():
                logging.info("Stopping Wind API connection.")
                w.stop()
        except Exception as exc:  # pragma: no cover - destructors rarely triggered in tests
            logging.warning("An error occurred while stopping the Wind API: %s", exc)

