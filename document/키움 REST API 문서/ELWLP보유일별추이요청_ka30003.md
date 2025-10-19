# ELWLP보유일별추이요청(ka30003)

| ◀ API 리스트 이동 | Unnamed: 1 | Unnamed: 2 | Unnamed: 3 | Unnamed: 4 | Unnamed: 5 | Unnamed: 6 |
| --- | --- | --- | --- | --- | --- | --- |
| 키움 REST API |  |  |  |  |  |  |
| API 정보 |  |  |  |  |  |  |
| 메뉴 위치 |  | 국내주식 > ELW > ELWLP보유일별추이요청(ka30003) |  |  |  |  |
| API 명 |  | ELWLP보유일별추이요청 |  |  |  |  |
| API ID |  | ka30003 |  |  |  |  |
| 기본정보 |  |  |  |  |  |  |
| Method |  | POST |  |  |  |  |
| 운영 도메인 |  | https://api.kiwoom.com |  |  |  |  |
| 모의투자 도메인 |  | https://mockapi.kiwoom.com(KRX만 지원가능) |  |  |  |  |
| URL |  | /api/dostk/elw |  |  |  |  |
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
| Body | bsis_aset_cd | 기초자산코드 | String | Y | 12 |  |
|  | base_dt | 기준일자 | String | Y | 8 | YYYYMMDD |
| Response |  |  |  |  |  |  |
| 구분 | Element | 한글명 | Type | Required | Length | Description |
| Header | api-id | TR명 | String | Y | 10 |  |
|  | cont-yn | 연속조회여부 | String | N | 1 | 다음 데이터가 있을시 Y값 전달 |
|  | next-key | 연속조회키 | String | N | 50 | 다음 데이터가 있을시 다음 키값 전달 |
| Body | elwlpposs_daly_trnsn | ELWLP보유일별추이 | LIST | N |  |  |
|  | - dt | 일자 | String | N | 20 |  |
|  | - cur_prc | 현재가 | String | N | 20 |  |
|  | - pre_tp | 대비구분 | String | N | 20 |  |
|  | - pred_pre | 전일대비 | String | N | 20 |  |
|  | - flu_rt | 등락율 | String | N | 20 |  |
|  | - trde_qty | 거래량 | String | N | 20 |  |
|  | - trde_prica | 거래대금 | String | N | 20 |  |
|  | - chg_qty | 변동수량 | String | N | 20 |  |
|  | - lprmnd_qty | LP보유수량 | String | N | 20 |  |
|  | - wght | 비중 | String | N | 20 |  |
| Request Example |  |  |  |  |  |  |
| {
    "bsis_aset_cd": "57KJ99",
    "base_dt": "20241122"
} |  |  |  |  |  |  |
| Response Example |  |  |  |  |  |  |
| {
    "elwlpposs_daly_trnsn": [
        {
            "dt": "20241122",
            "cur_prc": "-125700",
            "pre_tp": "5",
            "pred_pre": "-900",
            "flu_rt": "-0.71",
            "trde_qty": "54",
            "trde_prica": "7",
            "chg_qty": "0",
            "lprmnd_qty": "0",
            "wght": "0.00"
        }
    ],
    "return_code": 0,
    "return_msg": "정상적으로 처리되었습니다"
} |  |  |  |  |  |  |
