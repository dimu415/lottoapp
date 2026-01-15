HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
LOTTO_INFO_URL_500 = "https://www.dhlottery.co.kr/st/selectPblcnDsctnDtl.do?ntslWnSn=2231&_=1768461249321"
LOTTO_INFO_URL_1000 = "https://www.dhlottery.co.kr/st/selectPblcnDsctnDtl.do?ntslWnSn=2212&_=1768459620024"
LOTTO_INFO_URL_2000 = "https://www.dhlottery.co.kr/st/selectPblcnDsctnDtl.do?ntslWnSn=2139&_=1768460936641"

LOTTO_INFO_URLs=[LOTTO_INFO_URL_500,LOTTO_INFO_URL_1000,LOTTO_INFO_URL_2000]
new_json={}
for LOTTO_INFO_URL in LOTTO_INFO_URLs:
  res = requests.get(
      LOTTO_INFO_URL,
      params={"srchLtEpsd": "all"},
      headers=HEADERS
  )
  res.raise_for_status()

  data = res.json()
  result = data["data"]["result"]
  new_json[result["stGmTypeNm"]]={
            "game": {
                      "episode": result["stEpsd"],
                      "status": result["ntslStatus"],
                      "price": result["stNtslAmt"]
                  },
                  "sales": {
                      "publishQty": result["pblcnQty"],
                      "storeRate": result["stSpmtRt"],
                      "salesStart": result["stNtslBgngDt"],
                      "salesEnd": result["stNtslEndDt"],
                      "payEnd": result["stGiveEndDt"],
                      "payRate": result["stSumWnGiveRt"]
                  },
                  "ranks": []
              }
     
    

  for i in range(1, 6):
      new_json[result["stGmTypeNm"]]["ranks"].append({
          "rank": i,
          "prize": result[f"stRnk{i}GdsLstcCharCn"],
          "totalQty": result[f"stRnk{i}WnQty"],
          "paidQty": result[f"stRnk{i}WnCmptnQty"],
          "remainQty": result[f"stIvtRnk{i}Qty"]
      })
      
with open("Speetto.json", "w", encoding="utf-8") as f:
    json.dump(new_json, f, ensure_ascii=False, indent=2)
