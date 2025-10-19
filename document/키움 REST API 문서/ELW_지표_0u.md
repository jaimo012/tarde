# ELW 지표(0u)

| ◀ API 리스트 이동 | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| 키움 REST API |  |  |  |  |  |  |
| API 정보 |  |  |  |  |  |  |
| 메뉴 위치 |  | 국내주식 > 실시간시세 > ELW 지표(0u) |  |  |  |  |
| API 명 |  | ELW 지표 |  |  |  |  |
| API ID |  | 0u |  |  |  |  |
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
|  | - - 20 | 체결시간 | String | N |  |  |
|  | - - 666 | ELW패리티 | String | N |  |  |
|  | - - 1211 | ELW프리미엄 | String | N |  |  |
|  | - - 667 | ELW기어링비율 | String | N |  |  |
|  | - - 668 | ELW손익분기율 | String | N |  |  |
|  | - - 669 | ELW자본지지점 | String | N |  |  |
| Request Example |  |  |  |  |  |  |
| {
    "trnm": "REG",
    "grp_no": "1",
    "refresh": "1",
    "data": [
        {
            "item": [
                "57JBHH"
            ],
            "type": [
                "0u"
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
                '20': '111847',
                '666': '69.13',
                '1211': '0',
                '667': '1037.04',
                '668': '+44.73',
                '669': '+44.78'
            },
            'type': '0u',
            'name': 'ELW 지표',
            'item': '57JBHH'
        }
    ],
    'trnm': 'REAL'
} |  |  |  |  |  |  |
