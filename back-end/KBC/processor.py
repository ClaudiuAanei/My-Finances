import pandas as pd
import re
import json
from datetime import datetime
from KBC.data import stores


class CSVProcessor:
    """Parse KBC CSV exports and return normalized monthly transaction JSON."""

    NO_NAME = "No name assigned"
    NO_CATEGORY = "No category"
    INCOME_CATEGORY = "Income"

    NEEDED_COLUMNS = ["name", "description", "date", "amount", "currency"]
    EXPORT_COLUMNS = ["name", "description", "date", "amount", "currency", "category"]

    CARD_PAYMENT_PATTERN = re.compile(r"TIME\s+(.*?)\s+WITH", re.IGNORECASE)
    DIRECT_DEBIT_PATTERN = re.compile(
        r"CREDITOR\s*:\s*(.*?)\s+(?:CREDITOR REF|MANDATE REF|REFERENCE)", re.IGNORECASE
    )
    RECEIVED_PAYMENT_PATTERN = re.compile(
        r"ORDERING BANK:\s*(?:\S+\s+)?(.*?)\s*(?:/[A-Z]/|REFERENCE:|FILE REFERENCE)",
        re.IGNORECASE,
    )
    SENT_PAYMENT_PATTERN = re.compile(
        r"BENEFICIARY'S BANK:\s*(?:\S+)\s*(.*?)(?:\s+AT\s+\d{2}\.\d{2}|\s+WITH\s+KBC|\Z)",
        re.IGNORECASE,
    )
    CHARGE_PATTERN = re.compile(r"CHARGE\s+(.*?)\s+KBC", re.IGNORECASE)

    def __init__(self, input_file: str):
        """Initialize the processor with the input CSV path and store mapping."""
        self.input_file = input_file
        self.mapping = stores
        self.df = None

    def _find_company_name(self, description: str) -> str:
        """Find the first configured company key present in the raw description."""
        if pd.isna(description):
            return self.NO_NAME

        text = str(description).upper()
        for company in self.mapping:
            if company in text:
                return company

        return self.NO_NAME

    @staticmethod
    def _normalize_description_text(description: str) -> str:
        """Apply common cleanup so pattern extraction works on predictable text."""
        text = str(description)
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace(r"\/", "/").replace(r"\ /", "/").replace(r"\\", "")
        text = text.replace("AANEI CLAUDIU", "").strip()
        return re.sub(r"\s+", " ", text).strip()

    def _clean_description(self, description: str) -> str:
        """Extract a concise, user-friendly description from KBC raw transaction text."""
        if pd.isna(description):
            return ""

        text = self._normalize_description_text(description)

        # Match patterns in priority order and return on first hit.
        match_card = self.CARD_PAYMENT_PATTERN.search(text)
        if match_card:
            return match_card.group(1).strip()

        match_dd = self.DIRECT_DEBIT_PATTERN.search(text)
        if match_dd:
            return match_dd.group(1).strip()

        match_received = self.RECEIVED_PAYMENT_PATTERN.search(text)
        if match_received:
            return match_received.group(1).strip()

        match_sent = self.SENT_PAYMENT_PATTERN.search(text)
        if match_sent:
            details = match_sent.group(1).strip()
            return f"BENEFICIARY: {details}"

        match_charge = self.CHARGE_PATTERN.search(text)
        if match_charge:
            return f"CHARGE {match_charge.group(1).strip()}"

        # Fallback to cleaned text if no specialized rule matched.
        return text

    def _load_raw_dataframe(self) -> pd.DataFrame:
        """Load the CSV file using KBC export conventions."""
        try:
            return pd.read_csv(self.input_file, sep=";", decimal=",", index_col=False)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"File not found: {self.input_file}") from exc

    def _prepare_dataframe(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Keep required columns only and cast core fields to usable types."""
        df_raw.columns = df_raw.columns.str.lower()
        prepared_df = df_raw[self.NEEDED_COLUMNS].copy()
        prepared_df["date"] = pd.to_datetime(prepared_df["date"], dayfirst=True)
        prepared_df["amount"] = prepared_df["amount"].astype(float)
        return prepared_df

    def _enrich_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Populate normalized name, cleaned description, and derived category."""
        extracted_companies = df["description"].apply(self._find_company_name)
        df["name"] = extracted_companies
        df["description"] = df["description"].apply(self._clean_description)
        df["category"] = extracted_companies.map(self.mapping).fillna(self.NO_CATEGORY)

        # Positive amounts are treated as income regardless of company mapping.
        df.loc[df["amount"] > 0, "category"] = self.INCOME_CATEGORY
        return df

    def process(self):
        """Run the full import pipeline and cache the processed dataframe."""
        raw_df = self._load_raw_dataframe()
        prepared_df = self._prepare_dataframe(raw_df)
        self.df = self._enrich_dataframe(prepared_df)
        return self

    def get_monthly_json(self, target_month: int | None = None, target_year: int | None = None) -> str:
        """Return JSON records for the requested month/year, defaulting to current date."""
        if self.df is None:
            self.process()

        if self.df is None:
            raise ValueError("Failed to process data: dataframe is still None")

        now = datetime.now()
        month = target_month or now.month
        year = target_year or now.year

        mask = (self.df["date"].dt.month == month) & (self.df["date"].dt.year == year)
        result_df = self.df[mask].copy()

        result_df["date"] = result_df["date"].dt.strftime("%Y-%m-%d")

        records = result_df[self.EXPORT_COLUMNS].to_dict(orient="records")
        return json.dumps(records, indent=4)


if __name__ == "__main__":
    # This call uses your new "kbc.csv" file
    processor = CSVProcessor("../kbc.csv")

    # Print results for the selected month from the exported file
    print(processor.get_monthly_json(target_month=2, target_year=2026))