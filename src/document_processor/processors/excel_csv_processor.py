#!filepath: excel_csv_processor.py
"""
Excel/CSV processor for RAG Generator Tool.
Converts Excel and CSV files to Markdown format with tables.
"""

import os
import math
import logging
from typing import List, Tuple, Dict, Any, Optional
from ..config import ConverterConfig
from .base_processor import BaseDocumentProcessor

logger = logging.getLogger(__name__)

class ExcelCsvProcessor(BaseDocumentProcessor):
    """Processor for Excel and CSV files"""
    
    def __init__(self, config: ConverterConfig) -> None:
        super().__init__(config)
        self.max_rows_display = self.config.get('max_rows_display', 1000)
        self.max_columns_display = self.config.get('max_columns_display', 50)
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Return the file extensions supported by this processor"""
        return [".csv", ".xlsx", ".xls", ".tsv"]
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """Check if this processor can handle the file"""
        if not super().can_process(file_path):
            return False
        
        filename = os.path.basename(file_path)
        
        # Skip Excel temporary files
        if filename.startswith('~$'):
            return False
            
        # Check supported extensions
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.get_supported_extensions()

    def process(self, file_path: str, output_dir: str, media_dir: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process Excel/CSV file and convert to Markdown
        
        Args:
            file_path: Path to the Excel/CSV file
            output_dir: Directory for temporary extraction
            media_dir: Directory to save extracted media (not used for Excel/CSV)
            
        Returns:
            tuple: (markdown_content, metadata_dict)
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas library not installed. Install with: pip install pandas")
            return None, {
                'source_filename': os.path.basename(file_path),
                'parser': 'excel_csv_parser',
                'error': 'Missing dependency: pandas'
            }
        
        logger.info(f"Processing spreadsheet file: {file_path}")
        
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".csv":
                return self._process_csv_file(file_path, pd)
            elif ext == ".tsv":
                return self._process_tsv_file(file_path, pd)
            elif ext in [".xlsx", ".xls"]:
                return self._process_excel_file(file_path, pd)
            else:
                return None, {
                    'source_filename': os.path.basename(file_path),
                    'parser': 'excel_csv_parser',
                    'error': f'Unsupported format: {ext}'
                }
                
        except Exception as e:
            logger.error(f"Error processing spreadsheet file {file_path}: {e}", exc_info=True)
            return None, {
                'source_filename': os.path.basename(file_path),
                'parser': 'excel_csv_parser',
                'error': str(e)
            }

    def _process_csv_file(self, file_path: str, pd: Any) -> Tuple[str, Dict[str, Any]]:
        """Process CSV file with intelligent separator detection and special bundle handling.

        Args:
            file_path (str): Path to the CSV file.
            pd (Any): The pandas module.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the markdown content and metadata.
        """
        filename = os.path.basename(file_path)
        
        # Check if this is a bundle translation file
        if self._is_bundle_file(file_path):
            logger.info(f"Detected bundle translation file: {filename}")
            return self._process_bundle_file(file_path, pd)
        
        # Continue with regular CSV processing for non-bundle files
        return self._process_regular_csv_file(file_path, pd)

    def _is_bundle_file(self, file_path: str) -> bool:
        """Checks if the given file is a bundle translation file.

        Args:
            file_path (str): Path to the file.

        Returns:
            bool: True if it's a bundle file, False otherwise.
        """
        try:
            # Read first line to check if it starts with bundle,"key"
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                return first_line.startswith('bundle,"key"')
        except Exception:
            try:
                # Try with different encoding
                with open(file_path, 'r', encoding='latin-1') as f:
                    first_line = f.readline().strip()
                    return first_line.startswith('bundle,"key"')
            except Exception:
                return False

    def _process_bundle_file(self, file_path: str, pd: Any) -> Tuple[str, Dict[str, Any]]:
        """Processes bundle translation files with special handling.

        Args:
            file_path (str): Path to the bundle file.
            pd (Any): The pandas module.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the markdown content and metadata.
        """
        filename = os.path.basename(file_path)
        
        # Try different encodings for bundle files
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        df = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                # Bundle files use comma separator with proper quoting
                df = pd.read_csv(file_path, 
                            encoding=encoding,
                            sep=',',  # Bundle files always use comma
                            quotechar='"',  # Use double quotes
                            quoting=1,  # QUOTE_ALL - respect all quotes
                            skipinitialspace=True,  # Skip spaces after separator
                            dtype=str)  # Read as strings to preserve formatting
                
                used_encoding = encoding
                logger.info(f"Successfully parsed bundle file with {encoding} encoding")
                break
                
            except Exception as e:
                logger.debug(f"Failed to parse bundle file with {encoding}: {e}")
                continue
        
        if df is None:
            raise ValueError("Unable to parse bundle file with any encoding")
        
        # Process bundle-specific data
        original_rows = len(df)
        original_cols = len(df.columns)
        
        # Get language codes (all columns except 'bundle' and 'key')
        language_columns = [col for col in df.columns if col.lower() not in ['bundle', 'key']]
        
        # Clean up column names and data
        df.columns = [self._clean_column_name(col) for col in df.columns]
        
        # Clean up the data - remove extra spaces, quotes, and line breaks
        for col in df.columns:
            if col.lower() not in ['bundle']:  # Don't modify bundle names
                df[col] = df[col].astype(str).apply(self._clean_cell_content)
        
        # Truncate if necessary
        if len(df) > self.max_rows_display:
            df = df.head(self.max_rows_display)
            logger.info(f"Truncated bundle file to {self.max_rows_display} rows (original: {original_rows})")
        
        # Generate bundle-specific markdown content
        md_content = [f"# {filename} - Translation Bundle\n"]
        
        # Add bundle file information
        md_content.append(f"**File Type:** Translation Bundle (CSV)")
        md_content.append(f"**Encoding:** {used_encoding}")
        md_content.append(f"**Structure:** Bundle translations with quoted text support")
        md_content.append(f"**Languages:** {', '.join(language_columns)}")
        md_content.append(f"**Total Entries:** {original_rows} translation entries")
        md_content.append(f"**Total Languages:** {len(language_columns)}")
        
        if original_rows > self.max_rows_display:
            md_content.append(f"**Note:** Showing first {self.max_rows_display} entries out of {original_rows}")
        
        md_content.append("\n## Translation Data\n")
        
        # Convert to markdown table with bundle-specific formatting
        if not df.empty:
            md_table = self._format_bundle_table(df)
            md_content.append(md_table)
        else:
            md_content.append("*No translation data found*")
        
        # Add summary section
        if not df.empty:
            md_content.append(f"\n## Summary\n")
            
            # Count unique bundles
            unique_bundles = df['bundle'].nunique() if 'bundle' in df.columns else 0
            md_content.append(f"- **Unique Bundles:** {unique_bundles}")
            
            # Count translations per language
            for lang in language_columns:
                if lang in df.columns:
                    non_empty_translations = df[lang].notna().sum()
                    md_content.append(f"- **{lang.upper()} Translations:** {non_empty_translations}")
        
        # Generate metadata
        metadata = {
            'source_filename': filename,
            'parser': 'pandas_bundle_csv',
            'file_type': 'Translation Bundle',
            'encoding': used_encoding,
            'separator': ',',
            'languages': language_columns,
            'total_entries': original_rows,
            'total_languages': len(language_columns),
            'unique_bundles': df['bundle'].nunique() if not df.empty and 'bundle' in df.columns else 0,
            'displayed_entries': len(df),
            'column_names': list(df.columns)
        }
        
        return "\n".join(md_content), metadata

    def _format_bundle_table(self, df: Any) -> str:
        """Formats bundle data as a markdown table.

        Args:
            df (Any): The pandas DataFrame containing bundle data.

        Returns:
            str: The formatted markdown table.
        """
        try:
            # Use pandas to_markdown with bundle-specific formatting
            return df.to_markdown(index=False, tablefmt="github")
        except ImportError:
            # Fallback to manual table creation
            return self._create_bundle_table_fallback(df)

    def _create_bundle_table_fallback(self, df: Any) -> str:
        """Creates a bundle table manually when tabulate is not available.

        Args:
            df (Any): The pandas DataFrame containing bundle data.

        Returns:
            str: The manually created markdown table.
        """
        if df.empty:
            return "*No translation data to display*"
        
        # Create header row
        headers = list(df.columns)
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        
        # Create separator row
        separator_row = "| " + " | ".join("---" for _ in headers) + " |"
        
        # Create data rows with special handling for long translations
        data_rows = []
        for _, row in df.iterrows():
            row_data = []
            for i, (col, cell) in enumerate(zip(headers, row)):
                # Avoid pandas dependency here; handle common empty/NaN cases
                if (
                    cell is None
                    or (isinstance(cell, float) and math.isnan(cell))
                    or str(cell).strip().lower() in ['nan', 'none', 'null']
                ):
                    row_data.append("")
                else:
                    cell_str = str(cell)
                    # Escape pipe characters
                    cell_str = cell_str.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
                    
                    # For translation columns (not bundle/key), allow longer text but truncate if excessive
                    if col.lower() not in ['bundle', 'key'] and len(cell_str) > 150:
                        cell_str = cell_str[:147] + "..."
                    elif len(cell_str) > 50 and col.lower() in ['bundle', 'key']:
                        cell_str = cell_str[:47] + "..."
                    
                    row_data.append(cell_str)
            
            data_row = "| " + " | ".join(row_data) + " |"
            data_rows.append(data_row)
        
        # Combine all parts
        table_parts = [header_row, separator_row] + data_rows
        return "\n".join(table_parts)

    def _process_regular_csv_file(self, file_path: str, pd: Any) -> Tuple[str, Dict[str, Any]]:
        """Processes regular CSV files (non-bundle files).

        Args:
            file_path (str): Path to the CSV file.
            pd (Any): The pandas module.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the markdown content and metadata.
        """
        filename = os.path.basename(file_path)
        
        # Try different encodings and separators
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        separators = [';', ',', '\t']
        
        best_result = None
        best_score = -1
        
        # Test all combinations and score them
        for encoding in encodings:
            for sep in separators:
                try:
                    # Use more lenient parsing for scoring
                    df = pd.read_csv(file_path, 
                                encoding=encoding, 
                                sep=sep, 
                                nrows=100,  # Sample first 100 rows
                                on_bad_lines='skip',  # Skip problematic lines during scoring
                                dtype=str)  # Read everything as string to avoid type errors
                                
                    score = self._score_csv_parsing(df, sep, file_path, encoding)
                    
                    logger.debug(f"Encoding: {encoding}, Separator: '{sep}', Score: {score}, Columns: {len(df.columns)}")
                    
                    if score > best_score:
                        best_score = score
                        best_result = {
                            'encoding': encoding,
                            'separator': sep,
                            'score': score
                        }
                        
                except Exception as e:
                    logger.debug(f"Failed with encoding {encoding} and separator '{sep}': {e}")
                    continue
        
        if best_result is None:
            raise ValueError("Unable to parse CSV file with any common encoding/separator combination")
        
        # Now read the full file with the best configuration using multiple fallback strategies
        df = None
        parsing_strategy = None
        
        # Strategy 1: Try strict parsing first
        try:
            df = pd.read_csv(file_path, 
                            encoding=best_result['encoding'], 
                            sep=best_result['separator'],
                            dtype=str)  # Read as strings to avoid type conversion issues
            parsing_strategy = "strict"
            logger.info(f"Successfully parsed CSV with strict parsing")
            
        except Exception as e:
            logger.warning(f"Strict parsing failed: {e}")
            
            # Strategy 2: Skip bad lines
            try:
                df = pd.read_csv(file_path, 
                                encoding=best_result['encoding'], 
                                sep=best_result['separator'],
                                on_bad_lines='skip',  # Skip malformed lines
                                dtype=str)
                parsing_strategy = "skip_bad_lines"
                logger.info(f"Successfully parsed CSV by skipping bad lines")
                
            except Exception as e:
                logger.warning(f"Skip bad lines parsing failed: {e}")
                
                # Strategy 3: Use Python engine with more flexible parsing
                try:
                    df = pd.read_csv(file_path, 
                                    encoding=best_result['encoding'], 
                                    sep=best_result['separator'],
                                    engine='python',  # More flexible but slower
                                    on_bad_lines='skip',
                                    quoting=1,  # Handle quoted fields
                                    dtype=str)
                    parsing_strategy = "python_engine"
                    logger.info(f"Successfully parsed CSV with Python engine")
                    
                except Exception as e:
                    logger.warning(f"Python engine parsing failed: {e}")
                    
                    # Strategy 4: Most lenient - let pandas figure it out
                    try:
                        df = pd.read_csv(file_path, 
                                        encoding=best_result['encoding'], 
                                        sep=best_result['separator'],
                                        engine='python',
                                        on_bad_lines='skip',
                                        quoting=1,
                                        dtype=str)
                        parsing_strategy = "lenient"
                        logger.info(f"Successfully parsed CSV with lenient parsing")
                        
                    except Exception as e:
                        logger.error(f"All parsing strategies failed: {e}")
                        # Return error content instead of raising exception
                        return f"# Error Processing CSV\n\nFailed to process {filename}.\n\nError: {str(e)}", {
                            'source_filename': filename,
                            'parser': 'pandas_csv',
                            'error': str(e)
                        }
        
        if df is None or df.empty:
            return f"# Empty CSV File\n\nThe file {filename} appears to be empty or could not be read.", {
                'source_filename': filename,
                'parser': 'pandas_csv',
                'error': 'Empty or unreadable file'
            }
        
        logger.info(f"CSV parsed successfully - Strategy: {parsing_strategy}, Separator: '{best_result['separator']}', "
                f"Encoding: {best_result['encoding']}, Rows: {len(df)}, Columns: {len(df.columns)}")
        
        # Continue with existing processing logic...
        original_rows = len(df)
        original_cols = len(df.columns)
        
        if len(df) > self.max_rows_display:
            df = df.head(self.max_rows_display)
            logger.info(f"Truncated CSV to {self.max_rows_display} rows (original: {original_rows})")
        
        if len(df.columns) > self.max_columns_display:
            df = df.iloc[:, :self.max_columns_display]
            logger.info(f"Truncated CSV to {self.max_columns_display} columns (original: {original_cols})")
        
        # Generate markdown content
        md_content = [f"# {filename}\n"]
        
        # Add file info including parsing information
        md_content.append(f"**File Type:** CSV")
        md_content.append(f"**Encoding:** {best_result['encoding']}")
        md_content.append(f"**Separator:** '{best_result['separator']}'")
        md_content.append(f"**Parsing Strategy:** {parsing_strategy}")
        md_content.append(f"**Detection Score:** {best_result['score']:.2f}")
        md_content.append(f"**Dimensions:** {original_rows} rows × {original_cols} columns")
        
        if parsing_strategy in ["skip_bad_lines", "python_engine", "lenient"]:
            md_content.append(f"**Note:** Some malformed lines were skipped during parsing for data quality.")
        
        if original_rows > self.max_rows_display or original_cols > self.max_columns_display:
            md_content.append(f"**Display Note:** Data truncated for display (showing {len(df)} rows × {len(df.columns)} columns)")
        
        md_content.append("\n## Data\n")
        
        # Convert to markdown table
        if not df.empty:
            # Clean and prepare dataframe for LLM processing
            df_cleaned = self._sanitize_dataframe_for_conversion(df)
            
            # Clean column names
            df_cleaned.columns = [self._clean_column_name(col) for col in df_cleaned.columns]
            
            # Convert to markdown table
            md_table = self._dataframe_to_markdown(df_cleaned)
            md_content.append(md_table)
        else:
            md_content.append("*No data found in file*")
        
        # Generate metadata
        metadata = {
            'source_filename': filename,
            'parser': 'pandas_csv',
            'file_type': 'CSV',
            'encoding': best_result['encoding'],
            'separator': best_result['separator'],
            'parsing_strategy': parsing_strategy,
            'detection_score': best_result['score'],
            'total_rows': original_rows,
            'total_columns': original_cols,
            'displayed_rows': len(df),
            'displayed_columns': len(df.columns),
            'column_names': list(df.columns) if not df.empty else [],
            'had_parsing_issues': parsing_strategy != "strict"
        }
        
        return "\n".join(md_content), metadata

    def _score_csv_parsing(self, df: Any, separator: str, file_path: str, encoding: str) -> int:
        """Scores the quality of CSV parsing to choose the best separator.

        Args:
            df (Any): The pandas DataFrame.
            separator (str): The separator used.
            file_path (str): Path to the file.
            encoding (str): The encoding used.

        Returns:
            int: The score indicating parsing quality.
        """
        if df.empty:
            return 0
        
        score = 0
        
        # Base score: number of columns (more columns usually means better separation)
        num_columns = len(df.columns)
        score += num_columns * 10
        
        # Bonus for semicolon separator (your preference)
        if separator == ';':
            score += 15  # Preference bonus for semicolon
        
        # Penalty if we only got one column (likely wrong separator)
        if num_columns == 1:
            score -= 50
            
            # Check if the single column contains the separator we didn't use
            if not df.empty and len(df) > 0:
                first_cell = str(df.iloc[0, 0])
                if separator == ';' and ',' in first_cell:
                    score -= 100  # Heavy penalty - probably should use comma
                elif separator == ',' and ';' in first_cell:
                    score -= 100  # Heavy penalty - probably should use semicolon
        
        # Check consistency: do all rows have roughly the same number of fields?
        if num_columns > 1:
            try:
                # Read first few lines as raw text to check field consistency
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = [f.readline().strip() for _ in range(min(10, len(df) + 1))]
                
                # Count separators in each line
                separator_counts = [line.count(separator) for line in lines if line]
                if separator_counts:
                    # Bonus if separator count is consistent
                    if len(set(separator_counts)) == 1:
                        score += 20  # All lines have same number of separators
                    elif max(separator_counts) - min(separator_counts) <= 1:
                        score += 10  # Very consistent
                    else:
                        score -= 10  # Inconsistent separator count
                        
            except Exception:
                pass  # Ignore errors in consistency check
        
        # Check for reasonable data types in columns
        if num_columns > 1:
            # Bonus for having mixed data types (indicates proper column separation)
            numeric_cols = 0
            text_cols = 0
            
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    numeric_cols += 1
                elif df[col].dtype == 'object':
                    text_cols += 1
            
            if numeric_cols > 0 and text_cols > 0:
                score += 15  # Good mix of data types
        
        # Penalty for extremely wide tables (might indicate wrong separator)
        if num_columns > 100:
            score -= 30
        
        # Check if column names look reasonable (no obvious separator characters in headers)
        if num_columns > 1:
            header_quality = 0
            for col_name in df.columns:
                col_str = str(col_name)
                # Good if column names don't contain unused separators
                if separator != ',' and ',' not in col_str:
                    header_quality += 1
                elif separator != ';' and ';' not in col_str:
                    header_quality += 1
                elif separator != '\t' and '\t' not in col_str:
                    header_quality += 1
            
            score += header_quality * 2
        
        return max(0, score)  # Ensure non-negative score

    def _process_tsv_file(self, file_path: str, pd: Any) -> Tuple[str, Dict[str, Any]]:
        """Processes TSV file (Tab-Separated Values).

        Args:
            file_path (str): Path to the TSV file.
            pd (Any): The pandas module.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the markdown content and metadata.
        """
        filename = os.path.basename(file_path)
        
        try:
            # TSV files use tab separator
            df = pd.read_csv(file_path, sep='\t', encoding='utf-8')
            logger.info(f"Successfully parsed TSV with UTF-8 encoding")
        except UnicodeDecodeError:
            # Try alternative encodings
            logger.info(f"UTF-8 encoding failed for TSV, trying alternative encodings")
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file_path, sep='\t', encoding=encoding)
                    logger.info(f"Successfully parsed TSV with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    logger.debug(f"Failed to parse TSV with {encoding} encoding")
                    continue
            else:
                logger.error(f"All encoding attempts failed for TSV file: {filename}")
                raise ValueError("Unable to decode TSV file with any common encoding")
        
        # Use similar processing as CSV
        logger.info(f"Processing TSV dataframe with {len(df)} rows and {len(df.columns)} columns")
        return self._process_dataframe(df, filename, 'TSV', metadata_type='pandas_tsv')

    def _process_excel_file(self, file_path: str, pd: Any) -> Tuple[str, Dict[str, Any]]:
        """Processes Excel file (XLS/XLSX).

        Args:
            file_path (str): Path to the Excel file.
            pd (Any): The pandas module.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the markdown content and metadata.
        """
        filename = os.path.basename(file_path)
        
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            md_content = [f"# {filename}\n"]
            md_content.append(f"**File Type:** Excel")
            md_content.append(f"**Number of Sheets:** {len(sheet_names)}")
            md_content.append(f"**Sheet Names:** {', '.join(sheet_names)}\n")
            
            total_rows = 0
            total_cols = 0
            all_sheets_data = {}
            
            # Process each sheet
            for sheet_name in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    if df.empty:
                        md_content.append(f"## Sheet: {sheet_name}\n")
                        md_content.append("*No data found in this sheet*\n")
                        continue
                    
                    original_rows = len(df)
                    original_cols = len(df.columns)
                    total_rows += original_rows
                    total_cols = max(total_cols, original_cols)
                    
                    # Clean and prepare dataframe for LLM processing
                    df_cleaned = self._sanitize_dataframe_for_conversion(df)
                    
                    # Truncate if necessary (after cleaning)
                    if len(df_cleaned) > self.max_rows_display:
                        df_cleaned = df_cleaned.head(self.max_rows_display)
                    
                    if len(df_cleaned.columns) > self.max_columns_display:
                        df_cleaned = df_cleaned.iloc[:, :self.max_columns_display]
                    
                    # Clean column names
                    df_cleaned.columns = [self._clean_column_name(col) for col in df_cleaned.columns]
                    
                    # Add sheet content to markdown
                    md_content.append(f"## Sheet: {sheet_name}\n")
                    md_content.append(f"**Dimensions:** {original_rows} rows × {original_cols} columns")
                    
                    if original_rows > self.max_rows_display or original_cols > self.max_columns_display:
                        md_content.append(f" *(showing {len(df_cleaned)} rows × {len(df_cleaned.columns)} columns)*")
                    
                    md_content.append("\n")
                    
                    # Convert to markdown table
                    md_table = self._dataframe_to_markdown(df_cleaned)
                    md_content.append(md_table + "\n")
                    
                    # Store sheet data for metadata
                    all_sheets_data[sheet_name] = {
                        'rows': original_rows,
                        'columns': original_cols,
                        'column_names': list(df_cleaned.columns)
                    }
                    
                except Exception as e:
                    logger.warning(f"Error processing sheet '{sheet_name}': {e}")
                    md_content.append(f"## Sheet: {sheet_name}\n")
                    md_content.append(f"*Error processing this sheet: {str(e)}*\n")
            
            # Generate metadata
            metadata = {
                'source_filename': filename,
                'parser': 'pandas_excel',
                'file_type': 'Excel',
                'sheet_count': len(sheet_names),
                'sheet_names': sheet_names,
                'total_rows': total_rows,
                'max_columns': total_cols,
                'sheets_data': all_sheets_data
            }
            
            return "\n".join(md_content), metadata
            
        except Exception as e:
            logger.error(f"Error processing Excel file: {e}")
            raise
    
    def _process_dataframe(self, df: Any, filename: str, file_type: str, metadata_type: str) -> Tuple[str, Dict[str, Any]]:
        """Common processing logic for dataframes.

        Args:
            df (Any): The pandas DataFrame.
            filename (str): The original filename.
            file_type (str): The type of file (e.g., 'CSV', 'TSV').
            metadata_type (str): The parser name for metadata.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the markdown content and metadata.
        """
        logger.info(f"Processing {file_type} dataframe for {filename}")
        original_rows = len(df)
        original_cols = len(df.columns)
        logger.info(f"Original data dimensions: {original_rows} rows × {original_cols} columns")
        
        # Truncate data if too large
        if len(df) > self.max_rows_display:
            df = df.head(self.max_rows_display)
            logger.info(f"Truncated data to {self.max_rows_display} rows (original: {original_rows})")
        
        if len(df.columns) > self.max_columns_display:
            df = df.iloc[:, :self.max_columns_display]
            logger.info(f"Truncated data to {self.max_columns_display} columns (original: {original_cols})")
        
        # Generate markdown content
        md_content = [f"# {filename}\n"]
        md_content.append(f"**File Type:** {file_type}")
        md_content.append(f"**Dimensions:** {original_rows} rows × {original_cols} columns")
        
        if original_rows > self.max_rows_display or original_cols > self.max_columns_display:
            md_content.append(f"**Note:** Data truncated for display (showing {len(df)} rows × {len(df.columns)} columns)")
        
        md_content.append("\n## Data\n")
        
        # Convert to markdown table
        if not df.empty:
            # Clean column names
            df.columns = [self._clean_column_name(col) for col in df.columns]
            
            # Convert to markdown table
            md_table = self._dataframe_to_markdown(df)
            logger.info(f"Successfully created markdown table for {filename}")
            md_content.append(md_table)
        else:
            md_content.append("*No data found in file*")
        
        # Generate metadata
        metadata = {
            'source_filename': filename,
            'parser': metadata_type,
            'file_type': file_type,
            'total_rows': original_rows,
            'total_columns': original_cols,
            'displayed_rows': len(df),
            'displayed_columns': len(df.columns),
            'column_names': list(df.columns) if not df.empty else []
        }
        
        return "\n".join(md_content), metadata
    
    def _clean_column_name(self, col_name: Any) -> str:
        """Cleans column names for better markdown display.

        Args:
            col_name (Any): The original column name.

        Returns:
            str: The cleaned column name.
        """
        # Check for None, NaN, or empty values without using pandas
        if col_name is None or str(col_name).strip() in ['', 'nan', 'NaN', 'None']:
            return 'Unnamed_Column'
        
        # Convert to string and clean
        clean_name = str(col_name).strip()
        
        # Replace problematic characters
        clean_name = clean_name.replace('|', '_').replace('\n', ' ').replace('\r', ' ')
        
        # Limit length
        if len(clean_name) > 50:
            clean_name = clean_name[:47] + "..."
        
        return clean_name
    
    def _sanitize_dataframe_for_conversion(self, df: Any) -> Any:
        """Prepares a dataframe for LLM-friendly markdown conversion.

        Args:
            df (Any): The pandas DataFrame.

        Returns:
            Any: The sanitized DataFrame.
        """
        # Create a copy to avoid modifying original data
        df_cleaned = df.copy()
        # Replace NaN values with empty strings for better LLM interpretation
        df_cleaned = df_cleaned.fillna('')
        # Clean up text content in all cells
        for col in df_cleaned.columns:
            if df_cleaned[col].dtype == 'object':  # Text columns
                df_cleaned[col] = df_cleaned[col].astype(str).apply(self._clean_cell_content)
        
        return df_cleaned

    def _clean_cell_content(self, cell_value: Any) -> str:
        """Cleans individual cell content for markdown table compatibility.

        Args:
            cell_value (Any): The original cell value.

        Returns:
            str: The cleaned cell content.
        """
        if (cell_value is None or 
            cell_value == '' or 
            str(cell_value).strip() == '' or
            str(cell_value).lower() in ['nan', 'none', 'null']):
            return ''
        
        # Convert to string
        content = str(cell_value).strip()
        
        # Replace various types of line breaks with space
        content = content.replace('\r\n', ' ')  # Windows line breaks
        content = content.replace('\n', ' ')    # Unix line breaks  
        content = content.replace('\r', ' ')    # Mac line breaks
        
        # Replace multiple consecutive spaces with single space
        import re
        content = re.sub(r'\s+', ' ', content)
        
        # Escape markdown special characters that could break tables
        content = content.replace('|', '\\|')   # Escape pipe characters
        content = content.replace('[', '\\[')   # Escape square brackets
        content = content.replace(']', '\\]')
        
        # Limit extremely long cell content for readability
        if len(content) > 500:
            content = content[:497] + "..."
        
        return content.strip()    
    
    def _dataframe_to_markdown(self, df: Any) -> str:
        """Converts a dataframe to a markdown table with LLM-friendly formatting.

        Args:
            df (Any): The pandas DataFrame.

        Returns:
            str: The markdown table string.
        """
        # Clean the dataframe first
        df_clean = self._sanitize_dataframe_for_conversion(df)
        
        try:
            # Try using pandas built-in to_markdown (requires tabulate)
            return df_clean.to_markdown(index=False, tablefmt="github")
        except ImportError:
            logger.warning("tabulate library not available, using fallback markdown table generation")
            return self._create_markdown_table_fallback(df_clean)

    def _create_markdown_table_fallback(self, df: Any) -> str:
        """Creates a markdown table manually when tabulate is not available.

        Args:
            df (Any): The pandas DataFrame.

        Returns:
            str: The manually created markdown table string.
        """
        if df.empty:
            return "*No data to display*"
        
        # Create header row
        headers = list(df.columns)
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        
        # Create separator row
        separator_row = "| " + " | ".join("---" for _ in headers) + " |"
        
        # Create data rows
        data_rows = []
        for _, row in df.iterrows():
            row_data = []
            for cell in row:
                # Handle empty/None values
                if cell is None or cell == '' or str(cell).strip() == '':
                    row_data.append("")
                else:
                    # Escape pipe characters and limit cell length
                    cell_str = str(cell).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
                    if len(cell_str) > 100:
                        cell_str = cell_str[:97] + "..."
                    row_data.append(cell_str)
            
            data_row = "| " + " | ".join(row_data) + " |"
            data_rows.append(data_row)
        
        # Combine all parts
        table_parts = [header_row, separator_row] + data_rows
        return "\n".join(table_parts)
