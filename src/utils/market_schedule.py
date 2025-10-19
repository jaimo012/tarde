"""
한국 주식시장 개장일 및 개장시간 체크 모듈

이 모듈은 한국 주식시장(KOSPI, KOSDAQ)의 개장일과 개장시간을 확인하여
시장이 열려있는 시간에만 DART 스크래핑이 실행되도록 합니다.
"""

from datetime import datetime, time, date
from typing import Optional, List, Tuple
import pytz
from loguru import logger


class KoreanMarketSchedule:
    """한국 주식시장 개장 스케줄 관리 클래스"""
    
    # 한국 시간대
    KST = pytz.timezone('Asia/Seoul')
    
    # 정규 개장시간 (09:00 ~ 15:30)
    REGULAR_OPEN_TIME = time(9, 0)
    REGULAR_CLOSE_TIME = time(15, 30)
    
    # 동시호가 시간 (08:30 ~ 09:00, 15:20 ~ 15:30)
    PRE_MARKET_START = time(8, 30)
    POST_MARKET_END = time(15, 30)
    
    def __init__(self):
        """시장 스케줄 클래스를 초기화합니다."""
        self.current_year = datetime.now(self.KST).year
        
        # 공휴일 및 휴장일 데이터 (연도별로 업데이트 필요)
        self.holidays_2025 = self._get_holidays_2025()
        self.holidays_2024 = self._get_holidays_2024()
        
        logger.info(f"한국 주식시장 스케줄러가 초기화되었습니다. (기준년도: {self.current_year})")
    
    def is_market_open_now(self) -> bool:
        """
        현재 시점에 시장이 열려있는지 확인합니다.
        
        Returns:
            bool: 시장 개장 여부
        """
        now = datetime.now(self.KST)
        return self.is_market_open_at_time(now)
    
    def is_market_open_at_time(self, check_time: datetime) -> bool:
        """
        특정 시점에 시장이 열려있는지 확인합니다.
        
        Args:
            check_time (datetime): 확인할 시점
            
        Returns:
            bool: 시장 개장 여부
        """
        # 한국 시간대로 변환
        if check_time.tzinfo is None:
            check_time = self.KST.localize(check_time)
        else:
            check_time = check_time.astimezone(self.KST)
        
        # 1. 주말 체크 (토요일=5, 일요일=6)
        if check_time.weekday() >= 5:
            logger.debug(f"주말이므로 시장 휴장: {check_time.strftime('%Y-%m-%d %A')}")
            return False
        
        # 2. 공휴일 체크
        if self._is_holiday(check_time.date()):
            logger.debug(f"공휴일이므로 시장 휴장: {check_time.strftime('%Y-%m-%d')}")
            return False
        
        # 3. 개장시간 체크
        current_time = check_time.time()
        if not (self.PRE_MARKET_START <= current_time <= self.POST_MARKET_END):
            logger.debug(f"개장시간 외이므로 시장 휴장: {current_time.strftime('%H:%M:%S')}")
            return False
        
        logger.debug(f"시장 개장 중: {check_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    
    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """
        특정 날짜가 거래일인지 확인합니다.
        
        Args:
            check_date (Optional[date]): 확인할 날짜 (None이면 오늘)
            
        Returns:
            bool: 거래일 여부
        """
        if check_date is None:
            check_date = datetime.now(self.KST).date()
        
        # 주말 체크
        if check_date.weekday() >= 5:
            return False
        
        # 공휴일 체크
        return not self._is_holiday(check_date)
    
    def get_next_trading_day(self, from_date: Optional[date] = None) -> date:
        """
        다음 거래일을 반환합니다.
        
        Args:
            from_date (Optional[date]): 기준 날짜 (None이면 오늘)
            
        Returns:
            date: 다음 거래일
        """
        if from_date is None:
            from_date = datetime.now(self.KST).date()
        
        # 하루씩 증가하면서 거래일 찾기
        check_date = from_date
        for _ in range(10):  # 최대 10일까지 확인
            check_date = date(check_date.year, check_date.month, check_date.day)
            from datetime import timedelta
            check_date = check_date + timedelta(days=1)
            
            if self.is_trading_day(check_date):
                return check_date
        
        # 10일 내에 거래일을 찾지 못한 경우 (비정상적인 상황)
        logger.warning("10일 내에 다음 거래일을 찾을 수 없습니다.")
        return check_date
    
    def get_market_status_message(self) -> str:
        """
        현재 시장 상태를 설명하는 메시지를 반환합니다.
        
        Returns:
            str: 시장 상태 메시지
        """
        now = datetime.now(self.KST)
        
        if self.is_market_open_now():
            current_time = now.time()
            
            if current_time < self.REGULAR_OPEN_TIME:
                return f"🔔 동시호가 시간 (개장 전) - {current_time.strftime('%H:%M')}"
            elif current_time < time(15, 20):
                return f"📈 정규 거래시간 - {current_time.strftime('%H:%M')}"
            else:
                return f"🔔 동시호가 시간 (장 마감 전) - {current_time.strftime('%H:%M')}"
        else:
            if not self.is_trading_day():
                if now.weekday() >= 5:
                    return f"🏖️ 주말 휴장 - {now.strftime('%Y-%m-%d %A')}"
                else:
                    return f"🏛️ 공휴일 휴장 - {now.strftime('%Y-%m-%d')}"
            else:
                current_time = now.time()
                if current_time < self.PRE_MARKET_START:
                    return f"🌙 장 시작 전 - 개장: {self.PRE_MARKET_START.strftime('%H:%M')}"
                else:
                    return f"🌆 장 마감 후 - 다음 개장: 익일 {self.PRE_MARKET_START.strftime('%H:%M')}"
    
    def _is_holiday(self, check_date: date) -> bool:
        """특정 날짜가 공휴일인지 확인합니다."""
        year = check_date.year
        
        if year == 2025:
            return check_date in self.holidays_2025
        elif year == 2024:
            return check_date in self.holidays_2024
        else:
            # 다른 연도의 경우 기본 공휴일만 체크 (신정, 추석, 크리스마스 등)
            return self._is_basic_holiday(check_date)
    
    def _is_basic_holiday(self, check_date: date) -> bool:
        """기본 공휴일 체크 (연도에 관계없이 고정된 날짜)"""
        month_day = (check_date.month, check_date.day)
        
        # 신정, 크리스마스 등 고정 공휴일
        fixed_holidays = [
            (1, 1),   # 신정
            (3, 1),   # 삼일절
            (5, 5),   # 어린이날
            (6, 6),   # 현충일
            (8, 15),  # 광복절
            (10, 3),  # 개천절
            (10, 9),  # 한글날
            (12, 25), # 크리스마스
        ]
        
        return month_day in fixed_holidays
    
    def _get_holidays_2025(self) -> List[date]:
        """2025년 공휴일 및 휴장일 목록"""
        return [
            # 신정 연휴
            date(2025, 1, 1),   # 신정
            
            # 설날 연휴
            date(2025, 1, 28),  # 설날 전날
            date(2025, 1, 29),  # 설날
            date(2025, 1, 30),  # 설날 다음날
            
            # 기타 공휴일
            date(2025, 3, 1),   # 삼일절
            date(2025, 5, 5),   # 어린이날
            date(2025, 5, 6),   # 부처님오신날
            date(2025, 6, 6),   # 현충일
            date(2025, 8, 15),  # 광복절
            
            # 추석 연휴 (예상 - 실제 날짜는 음력 기준으로 확인 필요)
            date(2025, 10, 5),  # 추석 전날
            date(2025, 10, 6),  # 추석
            date(2025, 10, 7),  # 추석 다음날
            date(2025, 10, 8),  # 추석 대체공휴일
            
            date(2025, 10, 3),  # 개천절
            date(2025, 10, 9),  # 한글날
            date(2025, 12, 25), # 크리스마스
            
            # 주식시장 특별 휴장일 (필요시 추가)
            # date(2025, 12, 31), # 연말 (보통 정상 거래)
        ]
    
    def _get_holidays_2024(self) -> List[date]:
        """2024년 공휴일 및 휴장일 목록"""
        return [
            # 신정 연휴
            date(2024, 1, 1),   # 신정
            
            # 설날 연휴
            date(2024, 2, 9),   # 설날 전날
            date(2024, 2, 10),  # 설날
            date(2024, 2, 11),  # 설날 다음날
            date(2024, 2, 12),  # 설날 대체공휴일
            
            # 기타 공휴일
            date(2024, 3, 1),   # 삼일절
            date(2024, 4, 10),  # 국회의원 선거일
            date(2024, 5, 5),   # 어린이날
            date(2024, 5, 6),   # 대체공휴일 (어린이날)
            date(2024, 5, 15),  # 부처님오신날
            date(2024, 6, 6),   # 현충일
            date(2024, 8, 15),  # 광복절
            
            # 추석 연휴
            date(2024, 9, 16),  # 추석 전날
            date(2024, 9, 17),  # 추석
            date(2024, 9, 18),  # 추석 다음날
            
            date(2024, 10, 3),  # 개천절
            date(2024, 10, 9),  # 한글날
            date(2024, 12, 25), # 크리스마스
        ]
    
    def should_run_scraping(self) -> Tuple[bool, str]:
        """
        현재 스크래핑을 실행해야 하는지 판단합니다.
        
        Returns:
            Tuple[bool, str]: (실행 여부, 상태 메시지)
        """
        if self.is_market_open_now():
            return True, f"✅ {self.get_market_status_message()}"
        else:
            next_trading_day = self.get_next_trading_day()
            return False, f"⏸️ {self.get_market_status_message()} | 다음 거래일: {next_trading_day.strftime('%Y-%m-%d')}"


# 전역 인스턴스 생성
market_schedule = KoreanMarketSchedule()


def is_market_open() -> bool:
    """현재 시장이 열려있는지 간단히 확인하는 함수"""
    return market_schedule.is_market_open_now()


def get_market_status() -> str:
    """현재 시장 상태를 반환하는 함수"""
    return market_schedule.get_market_status_message()


def should_run_dart_scraping() -> Tuple[bool, str]:
    """DART 스크래핑 실행 여부를 판단하는 함수"""
    return market_schedule.should_run_scraping()


def is_trading_hours(allow_buy: bool = False) -> bool:
    """
    현재 시간이 거래 가능 시간인지 확인합니다.
    
    Args:
        allow_buy: True면 매수 가능 시간(09:00~15:20), False면 매도 가능 시간(09:00~15:30)
        
    Returns:
        bool: 거래 가능 시간 여부
    """
    now = datetime.now(KoreanMarketSchedule.KST)
    current_time = now.time()
    
    # 거래일인지 확인
    if not market_schedule.is_trading_day():
        return False
    
    # 시간 확인
    regular_open = time(9, 0)
    
    if allow_buy:
        # 매수는 15:20까지만 가능 (마감 10분 전)
        buy_close = time(15, 20)
        return regular_open <= current_time <= buy_close
    else:
        # 매도는 15:30까지 가능
        regular_close = time(15, 30)
        return regular_open <= current_time <= regular_close