# VI발동|해제(1h)

| ◀ API 리스트 이동 | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| 키움 REST API |  |  |  |  |  |  |
| API 정보 |  |  |  |  |  |  |
| 메뉴 위치 |  | 국내주식 > 실시간시세 > VI발동/해제(1h) |  |  |  |  |
| API 명 |  | VI발동/해제 |  |  |  |  |
| API ID |  | 1h |  |  |  |  |
| 기본정보 |  |  |  |  |  |  |
| Method |  | POST |  |  |  |  |
| 운영 도메인 |  | wss://api.kiwoom.com:10000 |  |  |  |  |
| 모의투자 도메인 |  | wss://mockapi.kiwoom.com:10000(KRX만 지원가능) |  |  |  |  |
| URL |  | /api/dostk/websocket |  |  |  |  |
| Format |  | JSON |  |  |  |  |
| Content-Type |  | application/json;charset=UTF-8 |  |  |  |  |
| 개요 |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
| Request |  |  |  |  |  |  |
| 구분 | Element | 한글명 | Type | Required | Length | Description |
| Header | api-id | TR명 | String | Y | 10 |  |
|  | authorization | 접근토큰 | String | Y | 1000 | 토큰 지정시 토큰타입("Bearer") 붙혀서 호출 
 예) Bearer Egicyx... |
|  | cont-yn | 연속조회여부 | String | N | 1 | 응답 Header의 연속조회여부값이 Y일 경우 다음데이터 요청시 응답 Header의 cont-yn값 세팅 |
|  | next-key | 연속조회키 | String | N | 50 | 응답 Header의 연속조회여부값이 Y일 경우 다음데이터 요청시 응답 Header의 next-key값 세팅 |
| Body | trnm | 서비스명 | String | Y | 10 | REG : 등록 , REMOVE : 해지 |
|  | grp_no | 그룹번호 | String | Y | 4 |  |
|  | refresh | 기존등록유지여부 | String | Y | 1 | 등록(REG)시
0:기존유지안함 1:기존유지(Default)
 0일경우 기존등록한 item/type은 해지, 1일경우 기존등록한 item/type 유지
해지(REMOVE)시 값 불필요 |
|  | data | 실시간 등록 리스트 | LIST |  |  |  |
|  | - item | 실시간 등록 요소 | String | N | 100 | 거래소별 종목코드, 업종코드
(KRX:039490,NXT:039490_NX,SOR:039490_AL) |
|  | - type | 실시간 항목 | String | Y | 2 | TR 명(0A,0B....) |
| Response |  |  |  |  |  |  |
| 구분 | Element | 한글명 | Type | Required | Length | Description |
| Header | api-id | TR명 | String | Y | 10 |  |
|  | cont-yn | 연속조회여부 | String | N | 1 | 다음 데이터가 있을시 Y값 전달 |
|  | next-key | 연속조회키 | String | N | 50 | 다음 데이터가 있을시 다음 키값 전달 |
| Body | return_code | 결과코드 | String | N |  | 통신결과에대한 코드
(등록,해지요청시에만 값 전송 0:정상,1:오류 , 데이터 실시간 수신시 미전송) |
|  | return_msg | 결과메시지 | String | N |  | 통신결과에대한메시지 |
|  | trnm | 서비스명 | String | N |  | 등록,해지요청시 요청값 반환 , 실시간수신시 REAL 반환 |
|  | data | 실시간 등록리스트 | LIST | N |  |  |
|  | - type | 실시간항목 | String | N |  | TR 명(0A,0B....) |
|  | - name | 실시간 항목명 | String | N |  |  |
|  | - item | 실시간 등록 요소 | String | N |  | 종목코드 |
|  | - values | 실시간 값 리스트 | LIST | N |  |  |
|  | - - 9001 | 종목코드 | String | N |  |  |
|  | - - 302 | 종목명 | String | N |  |  |
|  | - - 13 | 누적거래량 | String | N |  |  |
|  | - - 14 | 누적거래대금 | String | N |  |  |
|  | - - 9068 | VI발동구분 | String | N |  |  |
|  | - - 9008 | KOSPI,KOSDAQ,전체구분 | String | N |  |  |
|  | - - 9075 | 장전구분 | String | N |  |  |
|  | - - 1221 | VI발동가격 | String | N |  |  |
|  | - - 1223 | 매매체결처리시각 | String | N |  |  |
|  | - - 1224 | VI해제시각 | String | N |  |  |
|  | - - 1225 | VI적용구분 | String | N |  | 정적/동적/동적+정적 |
|  | - - 1236 | 기준가격 정적 | String | N |  | 계약,주 |
|  | - - 1237 | 기준가격 동적 | String | N |  |  |
|  | - - 1238 | 괴리율 정적 | String | N |  |  |
|  | - - 1239 | 괴리율 동적 | String | N |  |  |
|  | - - 1489 | VI발동가 등락율 | String | N |  |  |
|  | - - 1490 | VI발동횟수 | String | N |  |  |
|  | - - 9069 | 발동방향구분 | String | N |  |  |
|  | - - 1279 | Extra Item | String | N |  |  |
| Request Example |  |  |  |  |  |  |
| {
    "trnm": "REG",
    "grp_no": "1",
    "refresh": "1",
    "data": [
        {
            "item": [
                ""
            ],
            "type": [
                "1h"
            ]
        }
    ]
} |  |  |  |  |  |  |
| Response Example |  |  |  |  |  |  |
| #요청
{
    'trnm': 'REG',
    'return_code': 0,
    'return_msg': ''
}

#실시간 수신
{
    'data': [
        {
            'values': {
                '9001':'005930',
                '302':'삼성전자',
                '13':'1077818',
                '14':'4201',
                '9068':'1',
                '9008':'101',
                '9075':'1',
                '1221':'4125',
                '1223':'111454',
                '1224':'111703',
                '1225':'정적',
                '1236':'3750',
                '1237':'0',
                '1238':'+10.00',
                '1239':'0.00',
                '1489':'+10.00',
                '1490':'1',
                '9069':'1',
                '1279':'+정적'
            },
            'type':'1h',
            'name':'VI발동/해제',
            'item':'005930'
        }
    ],
    'trnm':'REAL'
} |  |  |  |  |  |  |
