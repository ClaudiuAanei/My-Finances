import pandas as pd
import re
import json
from datetime import datetime
from KBC.data import stores

class CSVProcessor:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.mapping = stores
        self.df = None

    def _find_company_name(self, description: str) -> str:
        if pd.isna(description): return "No name assigned"
        text = str(description).upper()
        for company in self.mapping:
            if company in text: return company
        return "No name assigned"

    def _clean_description(self, description: str) -> str:
        """
        Analyze raw text from the KBC CSV and extract key information using regex.
        """
        if pd.isna(description): return ""
        text = str(description)

        # --- PRE-PROCESSING (General tricks) ---
        # 1. Normalize multiple spaces (e.g., "CREDITOR        : " -> "CREDITOR : ")
        text = re.sub(r'\s+', ' ', text).strip()

        # 2. Remove useless escape-like slash sequences
        text = text.replace(r'\/', '/').replace(r'\ /', '/').replace(r'\\', '')

        # 3. Remove your full name so descriptions are cleaner
        text = text.replace("AANEI CLAUDIU", "").strip()

        # 4. Clean spacing again in case removals left extra gaps
        text = re.sub(r'\s+', ' ', text).strip()

        # --- SPECIFIC RULES (Regex) ---

        # 1. Rule for card payments (e.g., Colruyt, Revolut)
        match_card = re.search(r'TIME\s+(.*?)\s+WITH', text, re.IGNORECASE)
        if match_card:
            return match_card.group(1).strip()

        # 2. Rule for direct debits (e.g., Proximus)
        match_dd = re.search(r'CREDITOR\s*:\s*(.*?)\s+(?:CREDITOR REF|MANDATE REF|REFERENCE)', text, re.IGNORECASE)
        if match_dd:
            return match_dd.group(1).strip()

        # 3. Rule for bank transfers / incoming payments (e.g., salary, Kidslife)
        # Skip the BIC code (first token) and stop at /A/, /B/, /C/ or REFERENCE
        match_received = re.search(r'ORDERING BANK:\s*(?:\S+\s+)?(.*?)\s*(?:/[A-Z]/|REFERENCE:|FILE REFERENCE)', text,
                                   re.IGNORECASE)
        if match_received:
            return match_received.group(1).strip()

        # 4. Rule for outgoing payments (e.g., rent, transfers to friends)
        # Ignore recipient bank BIC and extract name/details directly
        match_sent = re.search(r"BENEFICIARY'S BANK:\s*(?:\S+)\s*(.*?)(?:\s+AT\s+\d{2}\.\d{2}|\s+WITH\s+KBC|\Z)", text,
                               re.IGNORECASE)
        if match_sent:
            details = match_sent.group(1).strip()
            return f"BENEFICIARY: {details}"

        # 5. Rule for KBC account charges
        match_charge = re.search(r'CHARGE\s+(.*?)\s+KBC', text, re.IGNORECASE)
        if match_charge:
            return f"CHARGE {match_charge.group(1).strip()}"

        # Fallback: return original text with basic cleanup applied
        return text

    def process(self):
            try:
                # Read the CSV
                df_raw = pd.read_csv(self.input_file, sep=";", decimal=",", index_col=False)
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {self.input_file}")

            # Step 1: Force all CSV headers to lowercase
            df_raw.columns = df_raw.columns.str.lower()

            # Step 2: Define the columns we need (all lowercase)
            needed_cols = ["name", "description", "date", "amount", "currency"]
            
            # Select only expected columns
            self.df = df_raw[needed_cols].copy()

            # Step 3: Process values
            self.df['date'] = pd.to_datetime(self.df['date'], dayfirst=True)
            self.df['amount'] = self.df['amount'].astype(float)

            # Extract company names and clean descriptions
            extracted_companies = self.df['description'].apply(self._find_company_name)
            self.df['name'] = extracted_companies
            self.df['description'] = self.df['description'].apply(self._clean_description)

            # Map categories
            self.df['category'] = extracted_companies.map(self.mapping).fillna("No category")
            self.df.loc[self.df['amount'] > 0, 'category'] = "Income"

            return self

    def get_monthly_json(self, target_month: int | None = None, target_year: int | None = None) -> str:
        if self.df is None:
            self.process()

        if self.df is None:
            raise ValueError("Failed to process data: dataframe is still None")

        now = datetime.now()
        month = target_month or now.month
        year = target_year or now.year

        mask = (self.df['date'].dt.month == month) & (self.df['date'].dt.year == year)
        result_df = self.df[mask].copy()
        
        # Format date for JSON
        result_df['date'] = result_df['date'].dt.strftime('%Y-%m-%d')

        # Column names are aligned and lowercase
        columns_to_export = ["name", "description", "date", "amount", "currency", "category"]

        records = result_df[columns_to_export].to_dict(orient="records")
        return json.dumps(records, indent=4)


if __name__ == "__main__":
    # This call uses your new "kbc.csv" file
    processor = CSVProcessor("../kbc.csv")

    # Print results for the selected month from the exported file
    print(processor.get_monthly_json(target_month=2, target_year=2026))