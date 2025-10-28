"""
DART 보고서 분석 모듈

이 모듈은 다운로드한 보고서에서 계약 관련 정보를 추출하는 기능을 제공합니다.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from loguru import logger

from config.settings import REQUIRED_FIELDS
from utils.error_handler import get_error_handler


class ReportAnalyzer:
    """보고서 내용을 분석하여 필요한 데이터를 추출하는 클래스"""
    
    def __init__(self):
        """보고서 분석기를 초기화합니다."""
        self.header_patterns = {
            '판매ㆍ공급계약 내용': [
                r'1\.\s*판매ㆍ공급계약\s*내용',
                r'-\s*체결계약명',
                r'계약\s*내용'
            ],
            '계약상대방': [
                r'3\.\s*계약상대방',
                r'3\.\s*계약상대',
                r'계약\s*상대방'
            ],
            '계약(수주)일자': [
                r'8\.\s*계약\(수주\)일자',
                r'7\.\s*계약\(수주\)일자',
                r'계약\s*일자',
                r'수주\s*일자'
            ],
            '시작일': [
                r'시작일',
                r'계약\s*시작일',
                r'공급\s*시작일'
            ],
            '종료일': [
                r'종료일',
                r'계약\s*종료일',
                r'공급\s*종료일'
            ],
            '계약금액': [
                r'확정\s*계약금액',
                r'계약금액\s*총액\(원\)',
                r'계약금액\(원\)',
                r'계약\s*금액'
            ],
            '최근 매출액': [
                r'최근\s*매출액\(원\)',
                r'최근매출액\(원\)',
                r'최근\s*매출액'
            ],
            '매출액 대비 비율': [
                r'매출액\s*대비\(%\)',
                r'매출액대비\(%\)',
                r'매출액\s*대비\s*비율'
            ]
        }
        
        logger.info("보고서 분석기가 초기화되었습니다.")
    
    def analyze_report(self, html_content: str, rcept_no: str = None) -> Dict[str, Optional[str]]:
        """
        보고서 HTML 내용을 분석하여 계약 정보를 추출합니다.
        
        Args:
            html_content (str): 보고서 HTML 내용
            rcept_no (str): 접수번호 (오류 추적용, 선택사항)
            
        Returns:
            Dict[str, Optional[str]]: 추출된 계약 정보
        """
        error_handler = get_error_handler()
        
        # 1단계: 입력값 검증
        if not html_content:
            error_msg = "분석할 보고서 내용이 없습니다"
            logger.warning(error_msg)
            if error_handler:
                error_handler.handle_error(
                    error=ValueError(error_msg),
                    module="dart_api.analyzer",
                    operation="analyze_report",
                    severity="WARNING",
                    related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음"
                )
            return {}
        
        if not isinstance(html_content, str):
            error_msg = f"잘못된 HTML 내용 타입: {type(html_content)}"
            logger.error(error_msg)
            if error_handler:
                error_handler.handle_error(
                    error=TypeError(error_msg),
                    module="dart_api.analyzer",
                    operation="analyze_report", 
                    severity="ERROR",
                    related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                    additional_context={"content_type": str(type(html_content))}
                )
            return {}
        
        # HTML 길이 검증
        if len(html_content.strip()) < 100:
            error_msg = f"HTML 내용이 너무 짧음: {len(html_content)} 문자"
            logger.warning(error_msg)
            if error_handler:
                error_handler.handle_error(
                    error=ValueError(error_msg),
                    module="dart_api.analyzer",
                    operation="analyze_report",
                    severity="WARNING",
                    related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                    additional_context={"content_length": len(html_content)}
                )
            return {}
        
        try:
            # 2단계: 핵심 로직 실행
            logger.debug(f"보고서 분석 시작: {len(html_content):,} 문자")
            
            # BeautifulSoup으로 HTML 파싱
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                if not soup or not soup.get_text(strip=True):
                    raise ValueError("HTML 파싱 결과가 비어있음")
            except Exception as parse_error:
                if error_handler:
                    error_handler.handle_error(
                        error=parse_error,
                        module="dart_api.analyzer",
                        operation="analyze_report_parse",
                        severity="ERROR",
                        related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                        additional_context={"content_preview": html_content[:200]}
                    )
                logger.error(f"HTML 파싱 실패: {parse_error}")
                return {}
            
            # 각 필드별로 데이터 추출
            extracted_data = {}
            extraction_stats = {"success": 0, "failed": 0, "total": len(self.header_patterns)}
            
            for field_name, patterns in self.header_patterns.items():
                try:
                    value = self._find_value_with_fallbacks(soup, patterns)
                    extracted_data[field_name] = value
                    
                    if value and value.strip():
                        logger.debug(f"'{field_name}' 추출 성공: {value[:50]}...")
                        extraction_stats["success"] += 1
                    else:
                        logger.debug(f"'{field_name}' 추출 실패")
                        extraction_stats["failed"] += 1
                        
                except Exception as field_error:
                    logger.warning(f"'{field_name}' 필드 추출 중 오류: {field_error}")
                    extracted_data[field_name] = None
                    extraction_stats["failed"] += 1
                    
                    if error_handler:
                        error_handler.handle_error(
                            error=field_error,
                            module="dart_api.analyzer",
                            operation="analyze_report_field_extraction",
                            severity="WARNING",
                            related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                            additional_context={
                                "field_name": field_name,
                                "patterns_count": len(patterns) if patterns else 0
                            }
                        )
            
            # 3단계: 결과 검증
            success_rate = extraction_stats["success"] / extraction_stats["total"] * 100
            logger.info(f"보고서 분석 완료: {extraction_stats['success']}/{extraction_stats['total']} 필드 추출 성공 ({success_rate:.1f}%)")
            
            # 필수 필드 추출 실패 시 경고
            missing_required = []
            for required_field in REQUIRED_FIELDS:
                if not extracted_data.get(required_field):
                    missing_required.append(required_field)
            
            if missing_required:
                error_msg = f"필수 필드 누락: {missing_required}"
                logger.warning(error_msg)
                if error_handler:
                    error_handler.handle_error(
                        error=ValueError(error_msg),
                        module="dart_api.analyzer",
                        operation="analyze_report_validation",
                        severity="WARNING",
                        related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                        additional_context={
                            "missing_fields": missing_required,
                            "extracted_fields": list(extracted_data.keys()),
                            "success_rate": success_rate
                        }
                    )
            
            return extracted_data
            
        except MemoryError as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.analyzer",
                    operation="analyze_report",
                    severity="CRITICAL",
                    related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                    additional_context={"content_size": len(html_content)}
                )
            logger.error(f"메모리 부족으로 보고서 분석 실패: {e}")
            return {}
            
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.analyzer",
                    operation="analyze_report",
                    severity="ERROR",
                    related_stock=f"접수번호:{rcept_no}" if rcept_no else "알 수 없음",
                    additional_context={
                        "content_length": len(html_content),
                        "content_preview": html_content[:300] if html_content else None
                    }
                )
            logger.error(f"보고서 분석 중 예상치 못한 오류: {e}")
            return {}
    
    def _find_value_with_fallbacks(self, soup: BeautifulSoup, patterns: List[str]) -> Optional[str]:
        """
        여러 패턴을 시도하여 가장 먼저 찾아지는 유효한 값을 반환합니다.
        
        Args:
            soup (BeautifulSoup): 파싱된 HTML 객체
            patterns (List[str]): 검색할 패턴 목록
            
        Returns:
            Optional[str]: 찾은 값 (없으면 None)
        """
        for pattern in patterns:
            value = self._find_value_by_header(soup, pattern)
            if value and value.strip() != '-' and value.strip() != '':
                return value.strip()
        return None
    
    def _find_value_by_header(self, soup: BeautifulSoup, header_pattern: str) -> Optional[str]:
        """
        특정 헤더 패턴을 찾아 그 옆 셀의 값을 반환합니다.
        
        Args:
            soup (BeautifulSoup): 파싱된 HTML 객체
            header_pattern (str): 검색할 헤더 패턴 (정규식)
            
        Returns:
            Optional[str]: 찾은 값 (없으면 None)
        """
        try:
            # 정규식 패턴으로 헤더 찾기
            pattern = re.compile(header_pattern, re.IGNORECASE)
            
            # span 또는 td 태그에서 패턴 매칭
            header_tag = soup.find(['span', 'td', 'p', 'div'], string=pattern)
            
            if not header_tag:
                # 텍스트가 정확히 매칭되지 않는 경우, 부분 매칭 시도
                all_tags = soup.find_all(['span', 'td', 'p', 'div'])
                for tag in all_tags:
                    if tag.get_text() and pattern.search(tag.get_text()):
                        header_tag = tag
                        break
            
            if not header_tag:
                return None
            
            # 헤더 태그의 부모 td에서 다음 형제 td 찾기
            parent_td = header_tag.find_parent('td')
            if parent_td:
                next_td = parent_td.find_next_sibling('td')
                if next_td:
                    return next_td.get_text(strip=True)
            
            # 테이블 구조가 다른 경우, 다른 방법으로 시도
            # 같은 행(tr)에서 다음 셀 찾기
            parent_tr = header_tag.find_parent('tr')
            if parent_tr:
                all_tds = parent_tr.find_all('td')
                for i, td in enumerate(all_tds):
                    if pattern.search(td.get_text()):
                        # 다음 td가 있으면 그 값을 반환
                        if i + 1 < len(all_tds):
                            return all_tds[i + 1].get_text(strip=True)
            
            return None
            
        except Exception as e:
            logger.debug(f"헤더 패턴 '{header_pattern}' 검색 중 오류: {e}")
            return None
    
    def validate_extracted_data(self, data: Dict[str, Optional[str]]) -> bool:
        """
        추출된 데이터가 완전한지 검증합니다.
        
        Args:
            data (Dict[str, Optional[str]]): 추출된 데이터
            
        Returns:
            bool: 데이터가 완전하면 True, 불완전하면 False
        """
        missing_fields = []
        
        for field in REQUIRED_FIELDS:
            if not data.get(field) or data[field].strip() == '':
                missing_fields.append(field)
        
        if missing_fields:
            logger.info(f"필수 필드 누락: {', '.join(missing_fields)}")
            return False
        else:
            logger.info("모든 필수 필드가 추출되었습니다.")
            return True
    
    def clean_extracted_data(self, data: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
        """
        추출된 데이터를 정제합니다.
        
        Args:
            data (Dict[str, Optional[str]]): 원본 데이터
            
        Returns:
            Dict[str, Optional[str]]: 정제된 데이터
        """
        cleaned_data = {}
        
        for key, value in data.items():
            if value is None:
                cleaned_data[key] = None
                continue
            
            # 공통 정제 작업
            cleaned_value = value.strip()
            cleaned_value = re.sub(r'\s+', ' ', cleaned_value)  # 연속 공백 제거
            cleaned_value = cleaned_value.replace('\n', ' ').replace('\r', '')  # 개행문자 제거
            
            # 필드별 특별 정제
            if '금액' in key:
                # 금액 필드의 경우 숫자와 단위만 남기기
                cleaned_value = re.sub(r'[^\d,원억만천백십일]', '', cleaned_value)
            elif '일자' in key or '날짜' in key:
                # 날짜 필드의 경우 날짜 형식 정제
                cleaned_value = re.sub(r'[^\d\-\./년월일]', '', cleaned_value)
            
            # 빈 문자열이나 '-'는 None으로 처리
            if cleaned_value == '' or cleaned_value == '-':
                cleaned_value = None
            
            cleaned_data[key] = cleaned_value
        
        return cleaned_data
