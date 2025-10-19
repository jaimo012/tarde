"""
구글 스프레드시트 연동 클라이언트

이 모듈은 구글 스프레드시트와의 연동을 담당합니다.
데이터 읽기, 쓰기, 중복 확인 등의 기능을 제공합니다.
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, List, Optional, Tuple
from loguru import logger
import os

from config.settings import (
    SPREADSHEET_URL, 
    SHEET_NAMES, 
    SHEET_COLUMNS,
    ENVIRONMENT
)


class GoogleSheetsClient:
    """구글 스프레드시트와의 연동을 담당하는 클라이언트 클래스"""
    
    def __init__(self, service_account_file: Optional[str] = None):
        """
        구글 스프레드시트 클라이언트를 초기화합니다.
        
        Args:
            service_account_file (Optional[str]): 서비스 계정 JSON 파일 경로 (클라우드타입에서는 사용하지 않음)
        """
        self.service_account_file = service_account_file
        self.spreadsheet_url = SPREADSHEET_URL
        self.sheet_names = SHEET_NAMES
        self.sheet_columns = SHEET_COLUMNS
        self.document = None
        self.is_cloudtype = ENVIRONMENT == 'production'
        
        # 구글 API 권한 범위 설정
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        logger.info(f"구글 스프레드시트 클라이언트가 초기화되었습니다. (환경: {ENVIRONMENT})")
    
    def connect(self) -> bool:
        """
        구글 스프레드시트에 연결합니다.
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            if self.is_cloudtype:
                # 클라우드타입 환경: 환경변수에서 서비스 계정 정보 가져오기
                from config.cloudtype_settings import GOOGLE_SERVICE_ACCOUNT_INFO
                credentials = Credentials.from_service_account_info(
                    GOOGLE_SERVICE_ACCOUNT_INFO,
                    scopes=self.scope
                )
                logger.info("클라우드타입 환경에서 서비스 계정 정보를 사용합니다.")
            else:
                # 로컬 환경: JSON 파일 사용
                service_account_file = self.service_account_file or os.getenv('SERVICE_ACCOUNT_FILE', 'config/life-coordinator-a8de30e91786.json')
                credentials = Credentials.from_service_account_file(
                    service_account_file, 
                    scopes=self.scope
                )
                logger.info(f"로컬 환경에서 서비스 계정 파일을 사용합니다: {service_account_file}")
            
            # gspread 클라이언트 생성
            gc = gspread.authorize(credentials)
            
            # 스프레드시트 문서 열기
            self.document = gc.open_by_url(self.spreadsheet_url)
            
            logger.info("구글 스프레드시트 연결 성공")
            return True
            
        except Exception as e:
            logger.error(f"구글 스프레드시트 연결 실패: {e}")
            return False
    
    def get_worksheet_data(self, sheet_name: str) -> Tuple[Optional[object], Optional[pd.DataFrame]]:
        """
        지정된 시트의 데이터를 DataFrame으로 가져옵니다.
        
        Args:
            sheet_name (str): 시트 이름
            
        Returns:
            Tuple[Optional[object], Optional[pd.DataFrame]]: (워크시트 객체, 데이터프레임)
        """
        if not self.document:
            logger.error("스프레드시트에 연결되지 않았습니다. connect() 메서드를 먼저 호출하세요.")
            return None, None
        
        try:
            # 워크시트 가져오기
            worksheet = self.document.worksheet(sheet_name)
            
            # 모든 데이터 가져오기
            records = worksheet.get_all_values()
            
            if len(records) > 1:
                # 첫 번째 행을 헤더로 사용하여 DataFrame 생성
                df = pd.DataFrame(records[1:], columns=records[0])
            else:
                # 데이터가 없는 경우 빈 DataFrame 생성
                df = pd.DataFrame(columns=records[0] if records else [])
            
            logger.info(f"'{sheet_name}' 시트에서 {len(df)}개의 레코드를 가져왔습니다.")
            return worksheet, df
            
        except gspread.WorksheetNotFound:
            logger.error(f"'{sheet_name}' 시트를 찾을 수 없습니다.")
            return None, None
        except Exception as e:
            logger.error(f"'{sheet_name}' 시트 데이터 가져오기 실패: {e}")
            return None, None
    
    def get_company_list(self) -> Optional[pd.DataFrame]:
        """
        분석 대상 회사 목록을 가져옵니다.
        
        Returns:
            Optional[pd.DataFrame]: 분석 대상 회사 목록 (실패 시 None)
        """
        worksheet, df = self.get_worksheet_data(self.sheet_names['COMPANY_LIST'])
        
        if df is None:
            return None
        
        # '분석대상'이 TRUE인 회사만 필터링
        if '분석대상' in df.columns:
            filtered_df = df[df['분석대상'] == 'TRUE'].copy()
            logger.info(f"분석 대상 회사 {len(filtered_df)}개를 필터링했습니다.")
            return filtered_df
        else:
            logger.warning("'분석대상' 컬럼을 찾을 수 없습니다. 전체 목록을 반환합니다.")
            return df
    
    def get_existing_report_numbers(self) -> set:
        """
        기존에 처리된 보고서 접수번호 목록을 가져옵니다.
        
        Returns:
            set: 기존 접수번호 집합
        """
        existing_numbers = set()
        
        # '계약' 시트에서 접수번호 가져오기
        _, contract_df = self.get_worksheet_data(self.sheet_names['CONTRACT'])
        if contract_df is not None and '접수번호' in contract_df.columns:
            existing_numbers.update(contract_df['접수번호'].tolist())
        
        # '분석제외' 시트에서 접수번호 가져오기
        _, excluded_df = self.get_worksheet_data(self.sheet_names['EXCLUDED'])
        if excluded_df is not None and '접수번호' in excluded_df.columns:
            existing_numbers.update(excluded_df['접수번호'].tolist())
        
        # 빈 문자열 제거
        existing_numbers.discard('')
        existing_numbers.discard(None)
        
        logger.info(f"기존 처리된 보고서 {len(existing_numbers)}개를 확인했습니다.")
        return existing_numbers
    
    def prepare_data_for_sheet(self, data_list: List[Dict]) -> pd.DataFrame:
        """
        데이터 리스트를 시트 저장용 DataFrame으로 변환합니다.
        
        Args:
            data_list (List[Dict]): 저장할 데이터 목록
            
        Returns:
            pd.DataFrame: 시트 저장용 DataFrame
        """
        if not data_list:
            return pd.DataFrame()
        
        # DataFrame 생성
        df = pd.DataFrame(data_list)
        
        # 날짜 형식 변환
        if '접수일자' in df.columns:
            df['접수일자'] = pd.to_datetime(
                df['접수일자'], 
                format='%Y%m%d', 
                errors='coerce'
            ).dt.strftime('%Y-%m-%d')
        
        # 컬럼 순서 맞추기 (정의된 순서대로)
        df = df.reindex(columns=self.sheet_columns)
        
        # 빈 값을 빈 문자열로 채우기
        df = df.fillna('')
        
        return df
    
    def append_data_to_sheet(self, sheet_name: str, df: pd.DataFrame) -> bool:
        """
        DataFrame 데이터를 지정된 시트에 추가합니다.
        
        Args:
            sheet_name (str): 대상 시트 이름
            df (pd.DataFrame): 추가할 데이터
            
        Returns:
            bool: 추가 성공 여부
        """
        if df.empty:
            logger.info("추가할 데이터가 없습니다.")
            return True
        
        if not self.document:
            logger.error("스프레드시트에 연결되지 않았습니다.")
            return False
        
        try:
            # 워크시트 가져오기
            worksheet = self.document.worksheet(sheet_name)
            
            # 데이터를 리스트로 변환
            data_to_append = df.values.tolist()
            
            # 시트에 데이터 추가
            worksheet.append_rows(
                data_to_append, 
                value_input_option='USER_ENTERED'
            )
            
            logger.info(f"'{sheet_name}' 시트에 {len(data_to_append)}개의 데이터를 성공적으로 추가했습니다.")
            return True
            
        except Exception as e:
            logger.error(f"'{sheet_name}' 시트에 데이터 추가 실패: {e}")
            return False
    
    def save_contract_data(self, data_list: List[Dict]) -> bool:
        """
        계약 데이터를 '계약' 시트에 저장합니다.
        
        Args:
            data_list (List[Dict]): 저장할 계약 데이터 목록
            
        Returns:
            bool: 저장 성공 여부
        """
        if not data_list:
            logger.info("저장할 계약 데이터가 없습니다.")
            return True
        
        df = self.prepare_data_for_sheet(data_list)
        return self.append_data_to_sheet(self.sheet_names['CONTRACT'], df)
    
    def save_excluded_data(self, data_list: List[Dict]) -> bool:
        """
        분석 제외 데이터를 '분석제외' 시트에 저장합니다.
        
        Args:
            data_list (List[Dict]): 저장할 분석 제외 데이터 목록
            
        Returns:
            bool: 저장 성공 여부
        """
        if not data_list:
            logger.info("저장할 분석 제외 데이터가 없습니다.")
            return True
        
        df = self.prepare_data_for_sheet(data_list)
        return self.append_data_to_sheet(self.sheet_names['EXCLUDED'], df)
    
    def get_sheet_statistics(self) -> Dict[str, int]:
        """
        각 시트의 데이터 개수를 반환합니다.
        
        Returns:
            Dict[str, int]: 시트별 데이터 개수
        """
        stats = {}
        
        for sheet_key, sheet_name in self.sheet_names.items():
            _, df = self.get_worksheet_data(sheet_name)
            stats[sheet_name] = len(df) if df is not None else 0
        
        return stats
    
    def ensure_trading_history_sheet(self) -> bool:
        """
        거래내역 시트가 존재하는지 확인하고, 없으면 생성합니다.
        
        Returns:
            bool: 시트 준비 성공 여부
        """
        try:
            if not self.document:
                logger.error("스프레드시트에 연결되지 않았습니다.")
                return False
            
            sheet_name = "거래내역"
            
            # 시트 존재 여부 확인
            try:
                worksheet = self.document.worksheet(sheet_name)
                logger.debug(f"'{sheet_name}' 시트가 이미 존재합니다.")
                return True
            except gspread.exceptions.WorksheetNotFound:
                # 시트가 없으면 새로 생성
                logger.info(f"'{sheet_name}' 시트를 생성합니다...")
                worksheet = self.document.add_worksheet(title=sheet_name, rows=1000, cols=15)
                
                # 헤더 추가
                headers = [
                    '종목코드', '종목명', '매수일시', '매수가', '매수수량', '매수금액',
                    '매도일시', '매도가', '매도수량', '매도금액', '수익금', '수익률(%)', 
                    '상태', '사유', '주문번호'
                ]
                worksheet.append_row(headers)
                
                logger.info(f"'{sheet_name}' 시트를 성공적으로 생성했습니다.")
                return True
                
        except Exception as e:
            logger.error(f"거래내역 시트 준비 중 오류 발생: {e}")
            return False
    
    def save_buy_transaction(self, trade_info: Dict) -> bool:
        """
        매수 거래 정보를 거래내역 시트에 저장합니다.
        
        Args:
            trade_info: 거래 정보
                - stock_code: 종목코드
                - stock_name: 종목명
                - buy_time: 매수일시
                - executed_price: 체결가격
                - quantity: 체결수량
                - executed_amount: 체결금액
                - order_number: 주문번호
                
        Returns:
            bool: 저장 성공 여부
        """
        try:
            if not self.ensure_trading_history_sheet():
                return False
            
            worksheet = self.document.worksheet("거래내역")
            
            from decimal import Decimal
            buy_price = trade_info['executed_price']
            quantity = trade_info['quantity']
            buy_amount = trade_info['executed_amount']
            
            row_data = [
                trade_info['stock_code'],
                trade_info['stock_name'],
                trade_info['buy_time'].strftime('%Y-%m-%d %H:%M:%S'),
                float(buy_price),
                quantity,
                float(buy_amount),
                '',  # 매도일시 (아직 매도 안함)
                '',  # 매도가
                '',  # 매도수량
                '',  # 매도금액
                '',  # 수익금
                '',  # 수익률
                '보유중',
                '매수 체결',
                trade_info.get('order_number', '')
            ]
            
            worksheet.append_row(row_data, value_input_option='USER_ENTERED')
            logger.info(f"매수 거래 정보 저장 완료: {trade_info['stock_name']}")
            return True
            
        except Exception as e:
            logger.error(f"매수 거래 정보 저장 중 오류 발생: {e}")
            return False
    
    def update_sell_transaction(self, stock_code: str, sell_info: Dict) -> bool:
        """
        매도 거래 정보로 거래내역을 업데이트합니다.
        
        Args:
            stock_code: 종목코드
            sell_info: 매도 정보
                - sell_time: 매도일시
                - executed_price: 체결가격
                - quantity: 체결수량
                - profit_rate: 수익률
                - reason: 매도 사유
                
        Returns:
            bool: 업데이트 성공 여부
        """
        try:
            if not self.document:
                logger.error("스프레드시트에 연결되지 않았습니다.")
                return False
            
            worksheet = self.document.worksheet("거래내역")
            
            # 전체 데이터 가져오기
            all_records = worksheet.get_all_records()
            
            # 해당 종목의 보유중 거래 찾기
            for idx, record in enumerate(all_records):
                if record['종목코드'] == stock_code and record['상태'] == '보유중':
                    row_num = idx + 2  # 헤더 행 제외 및 1-based index
                    
                    from decimal import Decimal
                    buy_price = Decimal(str(record['매수가']))
                    buy_amount = Decimal(str(record['매수금액']))
                    sell_price = sell_info['executed_price']
                    quantity = sell_info['quantity']
                    sell_amount = sell_price * Decimal(str(quantity))
                    profit = sell_amount - buy_amount
                    profit_rate = sell_info['profit_rate']
                    
                    # 매도 정보 업데이트
                    worksheet.update_cell(row_num, 7, sell_info['sell_time'].strftime('%Y-%m-%d %H:%M:%S'))  # 매도일시
                    worksheet.update_cell(row_num, 8, float(sell_price))  # 매도가
                    worksheet.update_cell(row_num, 9, quantity)  # 매도수량
                    worksheet.update_cell(row_num, 10, float(sell_amount))  # 매도금액
                    worksheet.update_cell(row_num, 11, float(profit))  # 수익금
                    worksheet.update_cell(row_num, 12, float(profit_rate * 100))  # 수익률(%)
                    worksheet.update_cell(row_num, 13, '매도완료')  # 상태
                    worksheet.update_cell(row_num, 14, sell_info.get('reason', '매도 체결'))  # 사유
                    
                    logger.info(f"매도 거래 정보 업데이트 완료: {record['종목명']} (수익률: {profit_rate*100:.2f}%)")
                    return True
            
            logger.warning(f"보유중인 거래를 찾을 수 없습니다: {stock_code}")
            return False
            
        except Exception as e:
            logger.error(f"매도 거래 정보 업데이트 중 오류 발생: {e}")
            return False
    
    def get_latest_buy_transaction(self, stock_code: str) -> Optional[Dict]:
        """
        특정 종목의 최근 매수 거래 정보를 조회합니다.
        
        Args:
            stock_code: 종목코드
            
        Returns:
            Optional[Dict]: 거래 정보 (없으면 None)
                - buy_date: 매수일시
                - buy_price: 매수가
                - quantity: 수량
        """
        try:
            if not self.document:
                logger.error("스프레드시트에 연결되지 않았습니다.")
                return None
            
            worksheet = self.document.worksheet("거래내역")
            all_records = worksheet.get_all_records()
            
            # 해당 종목의 보유중 거래 찾기
            for record in reversed(all_records):  # 최신 거래부터 확인
                if record['종목코드'] == stock_code and record['상태'] == '보유중':
                    from datetime import datetime
                    from decimal import Decimal
                    
                    return {
                        'buy_date': datetime.strptime(record['매수일시'], '%Y-%m-%d %H:%M:%S'),
                        'buy_price': Decimal(str(record['매수가'])),
                        'quantity': int(record['매수수량'])
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"매수 거래 정보 조회 중 오류 발생: {e}")
            return None