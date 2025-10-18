"""
슬랙 알림 모듈

이 모듈은 신규 계약 정보를 슬랙으로 전송하는 기능을 제공합니다.
"""

import requests
import json
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime
from .stock_analyzer import StockAnalyzer, StockAnalysisResult


class SlackNotifier:
    """슬랙 웹훅을 통한 알림 전송 클래스"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        슬랙 알림 클래스를 초기화합니다.
        
        Args:
            webhook_url (Optional[str]): 슬랙 웹훅 URL
        """
        self.webhook_url = webhook_url
        self.is_enabled = bool(webhook_url)
        
        # 주식 분석기 초기화 (pykrx 기반, API 키 불필요)
        self.stock_analyzer = StockAnalyzer()
        
        if self.is_enabled:
            logger.info("슬랙 알림이 활성화되었습니다.")
        else:
            logger.warning("슬랙 웹훅 URL이 설정되지 않아 알림이 비활성화됩니다.")
    
    def send_new_contract_notification(self, contracts: List[Dict]) -> bool:
        """
        신규 계약 정보를 슬랙으로 전송합니다.
        
        Args:
            contracts (List[Dict]): 신규 계약 정보 목록
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            logger.debug("슬랙 알림이 비활성화되어 있습니다.")
            return True
        
        if not contracts:
            logger.debug("전송할 신규 계약이 없습니다.")
            return True
        
        try:
            for contract in contracts:
                # 각 계약별로 별도 메시지 전송 (차트 이미지 포함)
                message = self._create_contract_message(contract)
                success = self._send_to_slack(message)
                
                if not success:
                    logger.error(f"슬랙 알림 전송 실패: {contract.get('종목명', 'Unknown')}")
                else:
                    logger.info(f"슬랙 알림 전송 성공: {contract.get('종목명', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"슬랙 알림 전송 중 오류 발생: {e}")
            return False
    
    def _create_contract_message(self, contract: Dict) -> Dict:
        """
        계약 정보를 슬랙 메시지 형식으로 변환합니다.
        
        Args:
            contract (Dict): 계약 정보
            
        Returns:
            Dict: 슬랙 메시지 페이로드
        """
        # 주식 분석 수행
        try:
            analysis = self.stock_analyzer.analyze_stock_for_contract(contract)
        except Exception as e:
            logger.error(f"주식 분석 중 오류 발생: {e}")
            analysis = None
        
        # 색상 결정 (분석 점수 기반)
        if analysis and analysis.recommendation_score >= 7:
            color = "#FF4444"  # 빨간색 (매우 유망)
        elif analysis and analysis.recommendation_score >= 5:
            color = "#FFA500"  # 주황색 (유망)
        elif analysis and analysis.recommendation_score >= 3:
            color = "#36A64F"  # 초록색 (보통)
        else:
            color = "#808080"  # 회색 (주의)
        
        # 헤더 텍스트
        header_text = f"🚨 *신규 단일판매공급계약 발견!*"
        
        # ========== 섹션 1: 종목정보 ==========
        section1_fields = [
            {
                "title": "종목코드",
                "value": contract.get('종목코드', '정보 없음'),
                "short": True
            },
            {
                "title": "종목명",
                "value": contract.get('종목명', '정보 없음'),
                "short": True
            },
            {
                "title": "시장구분",
                "value": contract.get('시장구분', '정보 없음'),
                "short": True
            },
            {
                "title": "업종명",
                "value": contract.get('업종명', '정보 없음'),
                "short": True
            }
        ]
        
        # 업종 강조 표시
        if analysis and analysis.is_target_industry:
            section1_fields.append({
                "title": "⭐ 주목 업종",
                "value": f"✅ {analysis.industry_name}",
                "short": False
            })
        
        # ========== 섹션 2: 투자정보 ==========
        section2_fields = [
            {
                "title": "접수일자",
                "value": self._format_date(contract.get('접수일자', '')),
                "short": True
            },
            {
                "title": "계약(수주)일자",
                "value": self._format_date(contract.get('계약(수주)일자', '')),
                "short": True
            },
            {
                "title": "계약상대방",
                "value": contract.get('계약상대방', '정보 없음'),
                "short": True
            },
            {
                "title": "계약금액",
                "value": self._format_amount(contract.get('계약금액', '')),
                "short": True
            },
            {
                "title": "계약내용",
                "value": self._truncate_text(contract.get('판매ㆍ공급계약 내용', '정보 없음'), 150),
                "short": False
            },
            {
                "title": "계약기간",
                "value": f"{self._format_date(contract.get('시작일', ''))} ~ {self._format_date(contract.get('종료일', ''))}",
                "short": True
            },
            {
                "title": "최근 매출액",
                "value": self._format_amount(contract.get('최근 매출액', '')),
                "short": True
            },
            {
                "title": "매출액 대비 비율",
                "value": f"{contract.get('매출액 대비 비율', '0')}%",
                "short": True
            }
        ]
        
        # ========== 섹션 3: 분석의견 ==========
        if analysis:
            # 등락률 이모지
            change_emoji = "📈" if analysis.price_change_rate >= 0 else "📉"
            change_sign = "+" if analysis.price_change_rate >= 0 else ""
            
            section3_fields = [
                {
                    "title": "시가총액",
                    "value": f"{analysis.market_cap:,}억원",
                    "short": True
                },
                {
                    "title": "당일시가",
                    "value": f"{analysis.opening_price:,}원",
                    "short": True
                },
                {
                    "title": "현재가",
                    "value": f"{analysis.current_price:,}원",
                    "short": True
                },
                {
                    "title": f"등락률 {change_emoji}",
                    "value": f"{change_sign}{analysis.price_change_rate:+.2f}%",
                    "short": True
                },
                {
                    "title": "캔들 상태",
                    "value": "✅ 양봉" if analysis.is_positive_candle else "❌ 음봉",
                    "short": True
                },
                {
                    "title": "거래량 비율",
                    "value": f"{analysis.volume_ratio:.1f}배 {'✅' if analysis.volume_ratio >= 2.0 else '❌'}",
                    "short": True
                },
                {
                    "title": f"{analysis.market_type} 지수",
                    "value": f"{analysis.index_current:,.1f}",
                    "short": True
                },
                {
                    "title": "200일 이동평균",
                    "value": f"{analysis.index_ma200:,.1f}",
                    "short": True
                },
                {
                    "title": "📊 종합 분석",
                    "value": analysis.analysis_summary,
                    "short": False
                },
                {
                    "title": "🎯 추천점수",
                    "value": f"*{analysis.recommendation_score}/10점*",
                    "short": True
                }
            ]
        else:
            section3_fields = [{
                "title": "📊 분석 의견",
                "value": "❌ 주식 분석 데이터를 가져올 수 없습니다.",
                "short": False
            }]
        
        # 첨부파일 구성
        attachments = [
            {
                "color": color,
                "title": f"📋 {contract.get('종목명', '정보 없음')} ({contract.get('종목코드', '')})",
                "title_link": contract.get('보고서링크', ''),
                "fields": [],
                "ts": int(datetime.now().timestamp())
            }
        ]
        
        # 섹션별로 분리된 attachment 생성
        attachments[0]["fields"] = [
            {"title": "━━━━━━━━ 📌 종목정보 ━━━━━━━━", "value": "", "short": False}
        ] + section1_fields + [
            {"title": "", "value": "", "short": False},
            {"title": "━━━━━━━━ 💰 투자정보 ━━━━━━━━", "value": "", "short": False}
        ] + section2_fields + [
            {"title": "", "value": "", "short": False},
            {"title": "━━━━━━━━ 📊 분석의견 ━━━━━━━━", "value": "", "short": False}
        ] + section3_fields
        
        # Footer 추가
        attachments[0]["footer"] = f"접수번호: {contract.get('접수번호', '')} | DART 스크래핑 시스템"
        
        # 슬랙 메시지 페이로드
        payload = {
            "text": header_text,
            "attachments": attachments,
            "username": "DART 스크래핑 봇",
            "icon_emoji": ":chart_with_upwards_trend:"
        }
        
        # 차트 이미지가 있으면 이미지 URL 추가 (파일 업로드 필요)
        if analysis and analysis.chart_image_path:
            # 차트 이미지는 별도로 업로드하고 URL을 메시지에 포함
            chart_uploaded = self._upload_chart_image(analysis.chart_image_path, contract.get('종목명', 'Unknown'))
            if chart_uploaded:
                # 이미지가 업로드되면 메시지에 이미지 블록 추가
                payload["attachments"][0]["image_url"] = chart_uploaded
        
        return payload
    
    def _upload_chart_image(self, image_path: str, stock_name: str) -> Optional[str]:
        """
        차트 이미지를 슬랙에 업로드합니다.
        
        Args:
            image_path (str): 이미지 파일 경로
            stock_name (str): 종목명
            
        Returns:
            Optional[str]: 업로드된 이미지 URL (실패 시 None)
        """
        # 슬랙 웹훅은 직접 이미지 업로드를 지원하지 않음
        # 대신 임시로 차트 이미지를 텍스트로 표시하거나,
        # 별도의 파일 호스팅 서비스를 사용해야 함
        # 여기서는 로컬 파일 경로를 로그로만 남김
        logger.info(f"차트 이미지 생성됨: {image_path} ({stock_name})")
        
        # TODO: 실제 구현 시 이미지 호스팅 서비스 (예: imgur, AWS S3) 사용
        # 현재는 None 반환 (차트는 로컬에 저장됨)
        return None
    
    def _send_to_slack(self, message: Dict) -> bool:
        """
        슬랙 웹훅으로 메시지를 전송합니다.
        
        Args:
            message (Dict): 전송할 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(message),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug("슬랙 웹훅 전송 성공")
                return True
            else:
                logger.error(f"슬랙 웹훅 전송 실패: HTTP {response.status_code}")
                logger.error(f"응답 내용: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("슬랙 웹훅 전송 타임아웃")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"슬랙 웹훅 전송 중 네트워크 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"슬랙 웹훅 전송 중 예상치 못한 오류: {e}")
            return False
    
    def _format_amount(self, amount: str) -> str:
        """
        금액을 읽기 쉬운 형태로 포맷팅합니다.
        
        Args:
            amount (str): 원본 금액 문자열
            
        Returns:
            str: 포맷팅된 금액 문자열
        """
        if not amount or amount.strip() == '':
            return "정보 없음"
        
        # 숫자만 추출
        import re
        numbers = re.findall(r'[\d,]+', str(amount))
        if not numbers:
            return amount
        
        # 첫 번째 숫자 문자열 사용
        number_str = numbers[0].replace(',', '')
        
        try:
            number = int(number_str)
            
            # 억 단위로 변환
            if number >= 100000000:  # 1억 이상
                eok = number // 100000000
                remainder = number % 100000000
                if remainder == 0:
                    return f"{eok:,}억원"
                else:
                    man = remainder // 10000
                    if man > 0:
                        return f"{eok:,}억 {man:,}만원"
                    else:
                        return f"{eok:,}억 {remainder:,}원"
            elif number >= 10000:  # 1만 이상
                man = number // 10000
                remainder = number % 10000
                if remainder == 0:
                    return f"{man:,}만원"
                else:
                    return f"{man:,}만 {remainder:,}원"
            else:
                return f"{number:,}원"
                
        except ValueError:
            return amount
    
    def _format_date(self, date_str: str) -> str:
        """
        날짜를 읽기 쉬운 형태로 포맷팅합니다.
        
        Args:
            date_str (str): 원본 날짜 문자열
            
        Returns:
            str: 포맷팅된 날짜 문자열
        """
        if not date_str or date_str.strip() == '':
            return ""
        
        # 이미 YYYY-MM-DD 형식인 경우
        if '-' in date_str and len(date_str) == 10:
            return date_str
        
        # YYYYMMDD 형식인 경우
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            except:
                return date_str
        
        return date_str
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        텍스트를 지정된 길이로 자릅니다.
        
        Args:
            text (str): 원본 텍스트
            max_length (int): 최대 길이
            
        Returns:
            str: 잘린 텍스트
        """
        if not text:
            return "정보 없음"
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length-3] + "..."
    
    def send_system_notification(self, message: str, level: str = "info") -> bool:
        """
        시스템 알림을 슬랙으로 전송합니다.
        
        Args:
            message (str): 전송할 메시지
            level (str): 알림 레벨 (info, warning, error)
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        # 레벨별 이모지 및 색상
        level_config = {
            "info": {"emoji": ":information_source:", "color": "#36a64f"},
            "warning": {"emoji": ":warning:", "color": "#ff9500"},
            "error": {"emoji": ":x:", "color": "#ff0000"}
        }
        
        config = level_config.get(level, level_config["info"])
        
        payload = {
            "text": f"{config['emoji']} *DART 스크래핑 시스템*",
            "attachments": [
                {
                    "color": config["color"],
                    "text": message,
                    "footer": "DART 스크래핑 시스템",
                    "ts": int(datetime.now().timestamp())
                }
            ],
            "username": "DART 스크래핑 봇",
            "icon_emoji": ":robot_face:"
        }
        
        return self._send_to_slack(payload)
