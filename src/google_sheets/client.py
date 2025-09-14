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
