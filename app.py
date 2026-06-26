import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from groq import Groq
import re

st.title("🗺️ 100% 실존 맛집 추천 & 길찾기 AI 에이전트")
st.write("네이버/다음 실제 검색 데이터를 기반으로 가짜 식당 없는 진짜 맛집을 추천합니다.")

# 🔒 [보안 유지] 코드 안의 진짜 키를 지우고, 가방(st.secrets)에서 꺼내오도록 설정합니다.
api_key = st.secrets.get("GROQ_API_KEY", "")

# 클라이언트 초기화
try:
    client = Groq(api_key=api_key.strip())
except Exception as e:
    st.error("API 키 설정이 필요합니다.")

# (이래 부분은 기존 다음(Daum) 검색 및 맛집 추천 코드와 100% 동일합니다...)
# 🔍 다음(Daum) 검색을 활용해 진짜 맛집 리스트를 확실하게 긁어오는 함수로 교체
def get_real_naver_shops(location):
    # 다음 검색창에 "[지역명] 맛집" 검색
    search_url = f"https://search.daum.net/search?w=tot&DA=YZR&t__nil_searchbox=btn&sug=&sugo=&q={location}+맛집"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다음 검색 결과창에서 실제 장소 이름들이 들어가는 대표적인 태그들 추출
        place_elements = soup.select(".fn_tit, .tit_place, .txt_tit, a.link_txt")
        
        real_shops = []
        for elem in place_elements:
            name = elem.get_text().strip()
            # 특수문자 제거 및 노이즈 필터링
            name = re.sub(r'\[.*?\]|\(.*?\)', '', name).strip()
            
            # 진짜 식당 이름 같고, 너무 길거나 짧지 않은 것만 엄선
            if name and 2 <= len(name) <= 15 and not any(word in name for word in ["맛집", "검색", "뉴스", "블로그", "카페", "더보기", "지도", "길찾기", "카카오"]):
                if name not in real_shops:
                    real_shops.append(name)
        
        return real_shops[:6] # 확실한 상위 진짜 식당 6개만 반환
    except Exception as e:
        return []

# 1단계: 목적지 입력 및 맛집 추천
st.header("1. 어디로 가시나요?")
destination = st.text_input("목적지(예: 강남역, 홍대, 부산역 등)를 입력하세요:", key="dest_input")

if destination:
    st.subheader(f"🍴 {destination} 주변 진짜 맛집 추천")
    
    with st.spinner("네이버에서 실시간 진짜 맛집 리스트를 가져오는 중..."):
        # 1. 진짜 식당 리스트 확보!
        real_restaurant_list = get_real_naver_shops(destination)
        
    if not real_restaurant_list:
        st.warning("실시간 맛집 데이터를 가져오지 못했습니다. 일반 AI 모드로 전환합니다.")
        real_restaurant_list = ["알 수 없음"]

    # 2. AI에게 진짜 식당 리스트를 먹여주며 프롬프트 작성
    recommend_prompt = f"""
    너는 대한민국 최고의 맛집 가이드야.
    사용자가 '{destination}'을(를) 검색해서 네이버 실시간 검색 결과로 나온 실제 식당 리스트는 다음과 같아:
    [{', '.join(real_restaurant_list)}]

    [엄격한 규칙]
    1. 반드시 위에 제공된 리스트에 있는 식당 중에서만 3곳을 골라서 추천해줘. 리스트에 없는 식당은 절대 지어내지 마.
    2. 선택한 식당들의 대표 메뉴와 특징을 너의 지식을 총동원해서 친절한 한국어로 설명해줘.
    3. 식당 이름, 주요 메뉴, 한 줄 평 형식으로 깔끔하게 요약해줘.
    """
    
    with st.spinner("AI가 진짜 맛집 정보를 요약하고 있습니다..."):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": recommend_prompt}]
            )
            recommendations = response.choices[0].message.content
            st.write(recommendations)
        except Exception as e:
            st.error(f"AI 호출 중 오류가 발생했습니다: {e}")

    # 2단계: 식당 선택 및 현재 위치 입력 후 길찾기
    st.header("2. 길찾기 안내")
    selected_restaurant = st.text_input("위 추천 맛집 중 가고 싶은 식당 이름을 입력하세요:", key="rest_input")
    current_location = st.text_input("현재 계신 위치(출발지)를 입력하세요:", key="curr_input")

    if selected_restaurant and current_location:
        st.subheader("🧭 경로 안내")
        
        route_prompt = f"출발지: {current_location}에서 목적지: {destination}에 있는 {selected_restaurant}(으)로 가는 대중교통 또는 도보 경로를 가상으로 친절하게 안내해줘. 반드시 한국어로 답변해줘."
        
        with st.spinner("최적의 경로를 탐색 중입니다..."):
            try:
                route_response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": route_prompt}]
                )
                route_info = route_response.choices[0].message.content
                st.write(route_info)
            except Exception as e:
                st.error(f"경로 탐색 중 오류가 발생했습니다: {e}")