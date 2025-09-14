## 개발환경
    - 언어: Python
    - 서버: 클라우드타입
    - 배포: GitHub (https://github.com/jaimo012/tarde.git)

## 주식거래 API
    - 키움증권 API 사용
    - 가이드: https://openapi.kiwoom.com/guide/apiguide?dummyVal=0
    - 가이드파일: 키움 REST API 문서.pdf, 키움 REST API 문서.xlsx

## 전자공시시스템(Dart)
    - 공시검색 개발가이드 : https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
    - 공시서류원본파일 개발가이드 : https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003

## 규칙
    - 코드 작성에 앞서 API 가이드를 반드시 확인하여 코드를 작성합니다.
    - 코드를 작성 후 README.md 파일에 개발/수정 내용을 기록하고, 깃허브에 배포하는 것까지를 수행한다.
    - 오류가 날 수 있는 부분에는 디코딩을 위한 로그를 찍어서 오류를 수정할 데이터를 확보한다.

## Git 커밋 규칙
    - PowerShell에서 긴 커밋 메시지 작성 시 문제 방지를 위해 다음 규칙을 준수한다:
        1. 커밋 메시지는 간결하게 작성 (50자 이내 제목 + 필요시 본문)
        2. 다중 라인 커밋 시 임시 파일 사용 또는 단일 라인으로 작성
        3. git log 조회 시 항상 `| cat` 또는 `--oneline -n 숫자` 옵션 사용
        4. 커밋 전 반드시 `git status`로 상태 확인
        5. 커밋 메시지에 특수문자(→, ←) 사용 금지 (PowerShell 호환성)

## 슬랙 알림 규칙
    - 불필요한 스팸 알림 방지를 위해 다음 규칙을 준수한다:
        1. 휴장일에는 어떠한 알림도 전송하지 않음 (스팸 방지)
        2. 신규 계약이 발견되지 않았을 때는 완료 알림 전송하지 않음
        3. 신규 계약 발견 시에만 상세 분석 결과와 함께 알림 전송
        4. 개별 회사 처리 오류는 로그만 기록 (시스템 전체 영향 없음)
        5. 데이터 저장 실패 및 시스템 전체 오류만 에러 알림 전송