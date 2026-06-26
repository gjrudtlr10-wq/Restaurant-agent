import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
import re
import urllib.parse # 주소에 한글이 들어갈 수 있도록 인코딩해주는 도구

st.title("🗺️ 100% 실존 맛집 추천 & 진짜 길찾기 에이전트")
st.write("실시간 데이터와 실제 지도 서비스를 연동하여 할루시네이션이 전혀 없는 서비스를 제공합니다.")

# 🔒 [보안 유지] 스트림릿 클라우드의 비밀 주머니(Secrets)에서 키를 읽어옵니다.
api_key = st.secrets.get("GROQ_API_KEY", "")

# 클라이언트 초기화
try:
    client = Groq(api_key=api_key.strip())
except Exception as e:
    st.error("API 키 설정이 필요합니다.")

# 🔍 다음(Daum) 검색을 활용해 진짜 맛집 리스트를 긁어오는 함수
def get_real_daum_shops(location):
    search_url = f"https://search.daum.net/search?w=tot&DA=YZR&t__nil_searchbox=btn&sug=&sugo=&q={location}+맛집"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        place_elements = soup.select(".fn_tit, .tit_place, .txt_tit, a.link_txt")
        
        real_shops = []
        for elem in place_elements:
            name = elem.get_text().strip()
            name = re.sub(r'\[.*?\]|\(.*?\)', '', name).strip()
            if name and 2 <= len(name) <= 15 and not any(word in name for word in ["맛집", "검색", "뉴스", "블로그", "카페", "더보기", "지도", "길찾기", "카카오"]):
                if name not in real_shops:
                    real_shops.append(name)
        return real_shops[:6]
    except Exception as e:
        return []

# 1단계: 목적지 입력 및 맛집 추천
st.header("1. 어디로 가시나요?")
destination = st.text_input("목적지(예: 강남역, 홍대, 부산역 등)를 입력하세요:", key="dest_input")

if destination:
    st.subheader(f"🍴 {destination} 주변 진짜 맛집 추천")
    
    with st.spinner("실시간 진짜 맛집 리스트를 가져오는 중..."):
        real_restaurant_list = get_real_daum_shops(destination)
        
    if not real_restaurant_list:
        st.warning("실시간 맛집 데이터를 가져오지 못했습니다. 일반 AI 모드로 전환합니다.")
        real_restaurant_list = ["알 수 없음"]

    recommend_prompt = f"""
    너는 대한민국 최고의 맛집 가이드야.
    사용자가 '{destination}'을(를) 검색해서 나온 실제 식당 리스트는 다음과 같아:
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
    st.header("2. 진짜 길찾기 안내")
    selected_restaurant = st.text_input("위 추천 맛집 중 가고 싶은 식당 이름을 입력하세요:", key="rest_input")
    current_location = st.text_input("현재 계신 위치(출발지)를 입력하세요:", key="curr_input")

    if selected_restaurant and current_location:
        st.subheader("🧭 실제 지도 연결")
        st.write("AI의 가짜 안내 대신, 실제 카카오맵과 네이버맵의 정확한 실시간 경로 링크를 생성했습니다. 아래 버튼을 눌러 확인하세요!")
        
        # 🔗 한글 주소를 인터넷 링크용 글자로 변환 (URL 인코딩)
        encoded_start = urllib.parse.quote(current_location)
        encoded_end = urllib.parse.quote(f"{destination} {selected_restaurant}")
        
        # 실제 길찾기 URL 생성
        kakao_map_url = f"https://map.kakao.com/?sName={encoded_start}&eName={encoded_end}"
        naver_map_url = f"https://map.naver.com/index.nhn?slng=&slat=&stext={encoded_start}&elng=&elat=&etext={encoded_end}&menu=route"
        
        # 스트림릿 화면에 이쁜 버튼으로 배치
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("💛 카카오맵으로 실시간 길찾기", kakao_map_url, use_container_width=True)
        with col2:
            st.link_button("💚 네이버맵으로 실시간 길찾기", naver_map_url, use_container_width=True)