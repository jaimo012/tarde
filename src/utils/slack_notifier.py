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
    
    def send_critical_error(self, error_title: str, error_details: Dict, 
                           stack_trace: Optional[str] = None) -> bool:
        """
        치명적 오류를 매우 상세하게 슬랙으로 전송합니다.
        
        Args:
            error_title: 오류 제목
            error_details: 오류 상세 정보 딕셔너리
            stack_trace: 스택 트레이스 (선택사항)
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        try:
            import platform
            import sys
            import pytz
            
            # 한국 시간으로 변환
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst)
            
            # 기본 필드
            fields = [
                {
                    "title": "🕐 발생 시각 (KST)",
                    "value": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
                    "short": True
                },
                {
                    "title": "💻 시스템",
                    "value": f"{platform.system()} {platform.release()}",
                    "short": True
                },
                {
                    "title": "🐍 Python 버전",
                    "value": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    "short": True
                }
            ]
            
            # 상세 정보 추가
            for key, value in error_details.items():
                # 값이 너무 길면 자르기
                str_value = str(value)
                if len(str_value) > 500:
                    str_value = str_value[:497] + "..."
                
                fields.append({
                    "title": key,
                    "value": str_value,
                    "short": False
                })
            
            # 스택 트레이스 추가 (있는 경우)
            if stack_trace:
                # 스택 트레이스가 너무 길면 마지막 2000자만
                if len(stack_trace) > 2000:
                    stack_trace = "...\n" + stack_trace[-2000:]
                
                fields.append({
                    "title": "📋 스택 트레이스",
                    "value": f"```\n{stack_trace}\n```",
                    "short": False
                })
            
            payload = {
                "text": f"🚨🚨🚨 *긴급: 시스템 치명적 오류 발생!* 🚨🚨🚨\n\n*{error_title}*",
                "attachments": [
                    {
                        "color": "#FF0000",
                        "fields": fields,
                        "footer": "자동매매 시스템 - 긴급 알림",
                        "ts": int(datetime.now().timestamp())
                    }
                ],
                "username": "긴급 알림 봇",
                "icon_emoji": ":rotating_light:"
            }
            
            logger.info("치명적 오류 슬랙 알림 전송 중...")
            return self._send_to_slack(payload)
            
        except Exception as e:
            logger.error(f"치명적 오류 알림 전송 중 오류 발생: {e}")
            # 최소한의 알림이라도 보내기
            try:
                simple_payload = {
                    "text": f"🚨🚨🚨 긴급: {error_title}\n\n상세 정보 전송 실패. 즉시 로그를 확인하세요!",
                    "username": "긴급 알림 봇",
                    "icon_emoji": ":rotating_light:"
                }
                return self._send_to_slack(simple_payload)
            except:
                return False
    
    def send_buy_start_notification(self, stock_name: str, stock_code: str, 
                                    score: int, disclosure_info: Dict) -> bool:
        """
        매수 시작 알림을 전송합니다.
        
        Args:
            stock_name: 종목명
            stock_code: 종목코드
            score: 투자 점수
            disclosure_info: 공시 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        try:
            contract_amount = disclosure_info.get('계약금액', '정보 없음')
            contract_party = disclosure_info.get('계약상대방', '정보 없음')
            
            payload = {
                "text": f"🔵 *매수 거래 시작!*",
                "attachments": [
                    {
                        "color": "#0066CC",
                        "fields": [
                            {
                                "title": "종목",
                                "value": f"{stock_name} ({stock_code})",
                                "short": True
                            },
                            {
                                "title": "투자 점수",
                                "value": f"⭐ {score}/10점",
                                "short": True
                            },
                            {
                                "title": "계약금액",
                                "value": contract_amount,
                                "short": True
                            },
                            {
                                "title": "계약상대방",
                                "value": contract_party,
                                "short": True
                            }
                        ],
                        "footer": "자동매매 시스템",
                        "ts": int(datetime.now().timestamp())
                    }
                ],
                "username": "자동매매 봇",
                "icon_emoji": ":chart_with_upwards_trend:"
            }
            
            return self._send_to_slack(payload)
            
        except Exception as e:
            logger.error(f"매수 시작 알림 전송 중 오류 발생: {e}")
            return False
    
    def send_buy_execution_notification(self, stock_name: str, stock_code: str,
                                       quantity: int, price: float, amount: float) -> bool:
        """
        매수 체결 알림을 전송합니다.
        
        Args:
            stock_name: 종목명
            stock_code: 종목코드
            quantity: 체결 수량
            price: 체결 가격
            amount: 체결 금액
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        try:
            payload = {
                "text": f"✅ *매수 체결 완료!*",
                "attachments": [
                    {
                        "color": "#00CC00",
                        "fields": [
                            {
                                "title": "종목",
                                "value": f"{stock_name} ({stock_code})",
                                "short": False
                            },
                            {
                                "title": "체결가",
                                "value": f"{price:,.0f}원",
                                "short": True
                            },
                            {
                                "title": "수량",
                                "value": f"{quantity:,}주",
                                "short": True
                            },
                            {
                                "title": "총 금액",
                                "value": f"{amount:,.0f}원",
                                "short": False
                            }
                        ],
                        "footer": "자동매매 시스템",
                        "ts": int(datetime.now().timestamp())
                    }
                ],
                "username": "자동매매 봇",
                "icon_emoji": ":money_with_wings:"
            }
            
            return self._send_to_slack(payload)
            
        except Exception as e:
            logger.error(f"매수 체결 알림 전송 중 오류 발생: {e}")
            return False
    
    def send_sell_order_notification(self, stock_name: str, stock_code: str,
                                     sell_type: str, target_price: Optional[float],
                                     reason: str) -> bool:
        """
        매도 주문 설정 알림을 전송합니다.
        
        Args:
            stock_name: 종목명
            stock_code: 종목코드
            sell_type: 매도 유형 ('market' or 'limit')
            target_price: 목표가 (지정가인 경우)
            reason: 사유
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        try:
            if sell_type == 'market':
                order_info = "시장가 매도 주문"
                price_info = "시장가"
            else:
                order_info = "지정가 매도 주문"
                price_info = f"{target_price:,.0f}원"
            
            payload = {
                "text": f"📝 *매도 주문 설정*",
                "attachments": [
                    {
                        "color": "#FF9500",
                        "fields": [
                            {
                                "title": "종목",
                                "value": f"{stock_name} ({stock_code})",
                                "short": False
                            },
                            {
                                "title": "주문 유형",
                                "value": order_info,
                                "short": True
                            },
                            {
                                "title": "목표가",
                                "value": price_info,
                                "short": True
                            },
                            {
                                "title": "사유",
                                "value": reason,
                                "short": False
                            }
                        ],
                        "footer": "자동매매 시스템",
                        "ts": int(datetime.now().timestamp())
                    }
                ],
                "username": "자동매매 봇",
                "icon_emoji": ":bell:"
            }
            
            return self._send_to_slack(payload)
            
        except Exception as e:
            logger.error(f"매도 주문 알림 전송 중 오류 발생: {e}")
            return False
    
    def send_sell_execution_notification(self, stock_name: str, stock_code: str,
                                        quantity: int, buy_price: float, sell_price: float,
                                        profit_rate: float, reason: str) -> bool:
        """
        매도 체결 알림을 전송합니다.
        
        Args:
            stock_name: 종목명
            stock_code: 종목코드
            quantity: 체결 수량
            buy_price: 매수가
            sell_price: 매도가
            profit_rate: 수익률 (소수)
            reason: 매도 사유
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        try:
            buy_amount = buy_price * quantity
            sell_amount = sell_price * quantity
            profit = sell_amount - buy_amount
            
            # 수익/손실에 따라 색상 결정
            if profit_rate >= 0:
                color = "#00CC00"  # 녹색 (수익)
                emoji = "💰"
            else:
                color = "#CC0000"  # 빨간색 (손실)
                emoji = "📉"
            
            payload = {
                "text": f"{emoji} *매도 체결 완료!*",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "종목",
                                "value": f"{stock_name} ({stock_code})",
                                "short": False
                            },
                            {
                                "title": "매수가",
                                "value": f"{buy_price:,.0f}원",
                                "short": True
                            },
                            {
                                "title": "매도가",
                                "value": f"{sell_price:,.0f}원",
                                "short": True
                            },
                            {
                                "title": "수량",
                                "value": f"{quantity:,}주",
                                "short": True
                            },
                            {
                                "title": "수익률",
                                "value": f"{profit_rate*100:+.2f}%",
                                "short": True
                            },
                            {
                                "title": "실현 손익",
                                "value": f"{profit:+,.0f}원",
                                "short": False
                            },
                            {
                                "title": "매도 사유",
                                "value": reason,
                                "short": False
                            }
                        ],
                        "footer": "자동매매 시스템",
                        "ts": int(datetime.now().timestamp())
                    }
                ],
                "username": "자동매매 봇",
                "icon_emoji": ":moneybag:"
            }
            
            return self._send_to_slack(payload)
            
        except Exception as e:
            logger.error(f"매도 체결 알림 전송 중 오류 발생: {e}")
            return False
    
    def send_system_startup_notification(self, balance_info: Optional[Dict] = None, 
                                        position_info: Optional[Dict] = None,
                                        trading_enabled: bool = False,
                                        market_status: Optional[str] = None,
                                        is_market_open: bool = False,
                                        auth_failed: bool = False) -> bool:
        """
        시스템 시작 알림을 슬랙으로 전송합니다.
        
        Args:
            balance_info: 계좌 잔고 정보 (예수금 등)
            position_info: 보유 포지션 정보
            trading_enabled: 자동매매 활성화 여부
            market_status: 시장 상태 메시지
            is_market_open: 시장 개장 여부
            
        Returns:
            bool: 전송 성공 여부
        """
        if not self.is_enabled:
            return True
        
        try:
            import platform
            import pytz
            
            # 한국 시간으로 변환
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst)
            
            # 기본 필드
            fields = [
                {
                    "title": "🕐 시작 시각 (KST)",
                    "value": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
                    "short": True
                },
                {
                    "title": "💻 실행 환경",
                    "value": platform.system(),
                    "short": True
                }
            ]
            
            # 시장 상태 추가
            if market_status:
                market_emoji = "✅" if is_market_open else "⏸️"
                fields.append({
                    "title": "📊 시장 상태",
                    "value": f"{market_emoji} {market_status}",
                    "short": False
                })
            
            # 자동매매 상태
            if trading_enabled:
                fields.append({
                    "title": "🤖 자동매매",
                    "value": "✅ 활성화 (실거래 모드)",
                    "short": False
                })
            else:
                if auth_failed:
                    fields.append({
                        "title": "🤖 자동매매",
                        "value": "🚨 비활성화 - 키움 API 인증 실패!\n상세 오류 메시지를 확인하세요.",
                        "short": False
                    })
                else:
                    fields.append({
                        "title": "🤖 자동매매",
                        "value": "⚠️ 비활성화 (공시 모니터링만 실행)",
                        "short": False
                    })
            
            # 키움 API 연결 상태 (항상 표시)
            fields.append({
                "title": "🔌 키움 API 연결",
                "value": "━━━━━━━━━━━━━━━━━━━━",
                "short": False
            })
            
            # 예수금 정보 (항상 조회 시도)
            if balance_info:
                available = balance_info.get('available_amount', 0)
                total = balance_info.get('total_balance', 0)
                
                fields.extend([
                    {
                        "title": "💰 예수금 (주문가능금액)",
                        "value": f"✅ {available:,.0f}원",
                        "short": True
                    },
                    {
                        "title": "💵 총 평가금액",
                        "value": f"✅ {total:,.0f}원",
                        "short": True
                    }
                ])
            else:
                fields.append({
                    "title": "💰 예수금",
                    "value": "❌ 조회 실패 (키움 API 확인 필요)",
                    "short": False
                })
            
            # 보유 포지션 정보 (항상 조회 시도)
            if position_info:
                fields.append({
                    "title": "📊 보유 종목",
                    "value": f"✅ {position_info['stock_name']}({position_info['stock_code']}) - {position_info['quantity']:,}주\n현재가: {position_info['current_price']:,.0f}원 | 수익률: {position_info['profit_rate']:+.2f}%",
                    "short": False
                })
            else:
                fields.append({
                    "title": "📊 보유 종목",
                    "value": "ℹ️ 없음",
                    "short": False
                })
            
            # 메시지 색상 및 텍스트 결정
            if auth_failed:
                color = "#FF0000"  # 빨강 (인증 실패)
                status_text = "⚠️ 시스템이 시작되었으나 키움 API 인증에 실패했습니다!\n자동매매가 비활성화되었습니다. 긴급 조치가 필요합니다."
            elif not is_market_open:
                color = "#808080"  # 회색 (휴장)
                status_text = "시스템이 정상적으로 시작되었습니다. 시장 휴장 중이므로 모니터링을 대기합니다."
            elif trading_enabled:
                color = "#2eb886"  # 초록 (자동매매 활성화)
                status_text = "시스템이 정상적으로 시작되었습니다. 자동매매 모니터링을 시작합니다."
            else:
                color = "#ffa500"  # 주황 (공시 모니터링만)
                status_text = "시스템이 정상적으로 시작되었습니다. 공시 모니터링을 시작합니다."
            
            payload = {
                "text": "🚀 *자동매매 시스템 시작*",
                "attachments": [
                    {
                        "color": color,
                        "text": status_text,
                        "fields": fields,
                        "footer": "자동매매 시스템",
                        "ts": int(datetime.now().timestamp())
                    }
                ],
                "username": "시스템 알림 봇",
                "icon_emoji": ":rocket:"
            }
            
            logger.info("시스템 시작 알림 전송 중...")
            return self._send_to_slack(payload)
            
        except Exception as e:
            logger.error(f"시스템 시작 알림 전송 중 오류 발생: {e}")
            return False