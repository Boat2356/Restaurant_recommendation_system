import streamlit as st
import pandas as pd
import folium
from surprise import SVD, dump, Dataset, Reader
from collections import defaultdict
from streamlit_folium import st_folium
import time
from supabase import create_client, Client


# ดึง API key จากไฟล์ secret.toml
# supabase_url = st.secrets["SUPABASE_URL"]
# supabase_key = st.secrets["SUPABASE_KEY"]

# supabase: Client = create_client(supabase_url, supabase_key)

# Page setup
st.set_page_config(
    page_title="🍽️ Restaurant Recommender System",
    page_icon="🍔",
)
st.title("🍽️ Restaurant Recommender System")
st.sidebar.success("Welcome to Restaurant Recommender System")

# @st.cache_data
# def load_data_from_db():
#     response_restaurants = (supabase.table("restaurants").select("*").execute())    
#     data = pd.DataFrame(response_restaurants.data)
#     response_ratings = (supabase.table("reviews").select("*").execute())
#     ratings_data = pd.DataFrame(response_ratings.data)
#     ratings_data = ratings_data[['reviewerid', 'placeid', 'reviewerrated']]
#     return data, ratings_data

@st.cache_data
def load_data():
    # Check ว่ามี directory อยู่หรือไม่ ถ้าไม่มีก็สร้างใหม่
    """
    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)          
    url = 'https://drive.google.com/uc?id=1Etnr2GZkjHlELBqUw3vN0xwxhmXnes_4'
    output = os.path.join(output_dir, 'df_restaurants_explode.csv')
    gdown.download(url, output, quiet=False)
    """
    data = pd.read_csv('.\data\df_restaurants_explode.csv', encoding='utf-8', engine='python')
    ratings_data = data[['reviewerId', 'placeId', 'reviewerRated']]    
    return data, ratings_data

# @st.cache_resource
# def load_model_from_db():
#     bucket_name = "dumpmodel"
#     destination_path = ".\dump_model\dump_SVD_file.pkl"
#     with open(destination_path, "wb") as f:
#         response = (
#             supabase.storage
#             .from_(bucket_name)
#             .download("dump_model/dump_SVD_file.pkl")
#         )
#         f.write(response)
#     predictions, algo = dump.load(destination_path)
#     return predictions, algo

@st.cache_resource
def load_model():
    # Check ว่ามี directory อยู่หรือไม่ ถ้าไม่มีก็สร้างใหม่
    """
    output_dir = 'dump_model'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)    
    url = 'https://drive.google.com/uc?id=1NE4_BGxB_IZYseW8nV08j2YFowvS6l8y'
    output = os.path.join(output_dir, 'dump_SVD_file.pkl')
    """
    predictions, algo = dump.load('.\dump_model\dump_SVD_file.pkl') #dump_model\dump_SVD_file.pkl
    return predictions, algo


# data, ratings_data = load_data_from_db()
# predictions, algo = load_model_from_db()
data, ratings_data = load_data()
predictions, algo = load_model()

# Random restaurant selection (only one at a time)
def get_random_restaurant():
    return data.sample(1)['title'].iloc[0]

@st.cache_data
def create_folium_map(restaurant):
    m = folium.Map(location=[restaurant['lat'], restaurant['lng']], zoom_start=15)
    folium.Marker(
        location=[restaurant['lat'], restaurant['lng']],
        popup=restaurant['title'],
        tooltip=restaurant['title']
    ).add_to(m)
    return m

# ฟังก์ชันให้ผู้ใช้กรอกคะแนนทีละร้าน
def get_user_rating(restaurant_name, mode='rating', idx=None):
    restaurant = data[data['title'] == restaurant_name].iloc[0]
    
    # ดึง URL รูปภาพแรก (ถ้ามี)
    image_url = None
    if 'imageUrls' in restaurant and pd.notna(restaurant['imageUrls']):
        if isinstance(restaurant['imageUrls'], str):
            try:
                image_list = eval(restaurant['imageUrls'])
            except:
                image_list = []
        else:
            image_list = restaurant['imageUrls']
        
        if len(image_list) > 0:
            image_url = image_list[0]

    # สร้าง HTML สำหรับ Popup
    popup_content = f"""
    <div style="max-width: 300px; word-wrap: break-word;">
        <h4 style="margin-bottom: 5px; font-size: 16px; text-align: left;">{restaurant['title']}</h4>
        <p><a href='{restaurant['url']}' target='_blank'>View on Google Map</a></p>
    """
    if image_url:
        popup_content += f"<img src='{image_url}' style='width:300px;'>"
    else:
        popup_content += "<p>No image available</p>"       
    

    with st.container(border=True, height=700):
        # แสดงข้อมูลร้านอาหารในคอลัมน์เดียว
        st.markdown(f"""
        <div class="restaurant-card">
            <h3>{restaurant['title']}</h3>
            <p>🍽️ {restaurant['categoryName']}</p>
            <p>💰 {restaurant['price']}</p>
            <p>📍 {restaurant['address']}</p>
            <p>⭐ {restaurant['totalScore']:.1f}</p>
        </div>
        """, unsafe_allow_html=True)

        # สร้างแผนที่และเพิ่ม Marker
        m = folium.Map(location=[restaurant['lat'], restaurant['lng']], zoom_start=15)
        iframe = folium.IFrame(popup_content, width=300, height=300)
        folium.Marker(
            location=[restaurant['lat'], restaurant['lng']],
            popup=folium.Popup(iframe, show=True),
            tooltip=restaurant['title']
        ).add_to(m)
        
        # แสดงแผนที่
        map_key = f"map_{restaurant_name}_{mode}_{idx}" if idx is not None else f"map_{restaurant_name}_{mode}"
        st_folium(m, width=700, key=map_key)

    # ส่วนการให้คะแนน
    if mode == 'rating':
        # ใช้ st.feedback แทน st.slider
        selected = st.feedback("stars", key=f"feedback_{restaurant_name}_{idx}")
        
        # แปลงค่าจาก st.feedback เป็นคะแนน 1-5
        if selected is not None:
            rating = selected + 1  # st.feedback คืนค่า 0-4 (0 = 1 star, 4 = 5 stars)
            st.markdown(f"You rated **{restaurant_name}** with {rating} star(s).")
            return rating
        return None
    return None

# Initialize session states
if 'rated_restaurants' not in st.session_state:
    st.session_state.rated_restaurants = {}
if 'restaurants_to_rate' not in st.session_state:
    st.session_state.restaurants_to_rate = []
if 'rating_completed' not in st.session_state:
    st.session_state.rating_completed = False
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = pd.DataFrame()
    
# Check if we have filtered data from the Filter page
if 'filtered_restaurant_ids' in st.session_state and st.session_state.filtered_restaurant_ids:
    # Filter the data based on the IDs from the Filter page
    filtered_ids = st.session_state.filtered_restaurant_ids
    filtered_data = data[data['placeId'].isin(filtered_ids)]
    
    # Use filtered data instead of full data
    st.info(f"Using {len(filtered_ids)} filtered restaurants based on your preferences.")
    data_to_use = filtered_data
    
    # Option to clear filters
    if st.button("Clear Filters"):
        st.session_state.filtered_restaurant_ids = None
        st.rerun()
else:
    data_to_use = data
    st.info("Using all available restaurants. Use the Filter page first to narrow down choices.")

# UI Settings
# กำหนดจำนวนร้านอาหารที่จะให้คะแนนเป็น 3-10 ร้าน โดยค่าเริ่มต้นคือ 5 ร้าน
length_data_to_use = len(data_to_use.drop_duplicates(subset=['title']))
if length_data_to_use < 5:
    num_restaurants = st.sidebar.slider("Number of restaurants to rate:", length_data_to_use)
else:
    num_restaurants = st.sidebar.slider("Number of restaurants to rate:", min(3, length_data_to_use), min(10, length_data_to_use), 5)
    
num_recommendations = st.sidebar.slider("Number of recommendations to show:", 1, 10, 5)


# Initialize restaurants to rate if empty
if len(st.session_state.restaurants_to_rate) == 0 and not st.session_state.rating_completed:
    # ใช้ drop_duplicates ก่อนการสุ่ม เพื่อให้ไม่มีชื่อซ้ำ
    unique_restaurants = data_to_use.drop_duplicates(subset=['title'])
    
    # คำนวณจำนวนร้านที่จะสุ่มจริงๆ ไม่เกินจำนวนที่มีอยู่
    sample_count = min(num_restaurants, len(unique_restaurants))
    
    # สุ่มร้านอาหาร
    sampled = unique_restaurants.sample(n=sample_count)
    
    # เก็บเฉพาะชื่อร้าน
    st.session_state.restaurants_to_rate = sampled['title'].tolist()
    
    # อัปเดตจำนวนร้านที่ให้คะแนนจริงๆ ในกรณีที่มีน้อยกว่าที่กำหนด
    if sample_count < num_restaurants:
        st.warning(f"Only {sample_count} unique restaurants are available after filtering. Showing all of them.")

# เพิ่มการแสดงสถานะให้ชัดเจนยิ่งขึ้น
actual_restaurants = len(st.session_state.restaurants_to_rate) + len(st.session_state.rated_restaurants)
st.sidebar.write(f"Progress: {len(st.session_state.rated_restaurants)}/{actual_restaurants} rated")

# Rating Collection Phase
if not st.session_state.rating_completed:
    st.subheader("🍽️ Please rate these restaurants")
    
    # ตรวจสอบว่ามีร้านที่ต้องให้คะแนนหรือไม่
    if st.session_state.restaurants_to_rate:
        # สร้างตัวแปรเก็บคะแนนชั่วคราว
        if 'temp_ratings' not in st.session_state:
            st.session_state.temp_ratings = {}
            
        # ใช้ Accordion แทน Tabs
        for i, restaurant_name in enumerate(st.session_state.restaurants_to_rate):
            with st.expander(f"Restaurant #{i+1}: {restaurant_name}", expanded=(i == 0)):
                rating = get_user_rating(restaurant_name, idx=i)
                if rating is not None:
                    st.session_state.temp_ratings[restaurant_name] = rating
        
        # แสดงจำนวนร้านที่ได้รับการให้คะแนนแล้ว
        total_rated = len([r for r, rating in st.session_state.temp_ratings.items() if rating is not None])
        st.info(f"You have rated {total_rated}/{len(st.session_state.restaurants_to_rate)} restaurants.")
        
        # ปุ่มส่งคะแนนทั้งหมดพร้อมกัน
        if st.button("Submit All Ratings", type="primary"):
            # ดึงคะแนนจาก session state
            valid_ratings = {rest: rate for rest, rate in st.session_state.temp_ratings.items() if rate is not None}
            
            if not valid_ratings:
                st.warning("Please rate at least one restaurant before submitting.")
            else:
                # เพิ่มคะแนนที่ผู้ใช้ให้ไว้แล้ว
                st.session_state.rated_restaurants.update(valid_ratings)
                
                # กรองร้านที่ยังไม่ได้ให้คะแนนออกจากรายการ
                st.session_state.restaurants_to_rate = [
                    rest for rest in st.session_state.restaurants_to_rate 
                    if rest not in valid_ratings
                ]
                
                # รีเซ็ตคะแนนชั่วคราว
                st.session_state.temp_ratings = {}
                
                # ตรวจสอบว่าให้คะแนนครบตามที่กำหนดหรือไม่
                if len(st.session_state.rated_restaurants) >= actual_restaurants:
                    st.session_state.rating_completed = True
                    
                st.rerun()


# Recommendation Phase
if st.session_state.rating_completed and st.session_state.recommendations.empty:
    with st.spinner('Wait for it...'):
        time.sleep(5)
        st.success("Done!")
    st.subheader("Your Ratings Summary")
    ratings_df = pd.DataFrame(
        [(rest, rate) for rest, rate in st.session_state.rated_restaurants.items()],
        columns=['Restaurant', 'Your Rating']
    )
    #st.dataframe(ratings_df)   

    # Create new user ratings dataset
    new_user_ratings = []
    for restaurant, rating in st.session_state.rated_restaurants.items():
        place_id = data[data['title'] == restaurant]['placeId'].iloc[0]
        new_user_ratings.append(('new_user', place_id, float(rating)))
    
    # Combine with existing ratings
    df_combined = pd.concat([ratings_data, pd.DataFrame(new_user_ratings, columns=['reviewerId', 'placeId', 'reviewerRated'])]).reset_index(drop=True)
    
    # Train model with combined data
    reader = Reader(rating_scale=(1, 5))
    data_combined = Dataset.load_from_df(df_combined, reader)
    trainset_combined = data_combined.build_full_trainset()
    algo.fit(trainset_combined)
    
    # Get unrated restaurants
    rated_place_ids = [data[data['title'] == rest]['placeId'].iloc[0] 
                      for rest in st.session_state.rated_restaurants.keys()]
    all_restaurants = data['placeId'].unique()
    
    # Generate predictions
    predictions = []
    for place_id in all_restaurants:
        if place_id not in rated_place_ids:
            pred = algo.predict('new_user', place_id)
            predictions.append({
                'placeId': pred.iid,
                'predicted_rating': pred.est
            })
    
    # Create recommendations dataframe
    recommendations_df = pd.DataFrame(predictions)
    st.session_state.recommendations = (
        recommendations_df
        .sort_values('predicted_rating', ascending=False)
        .head(num_recommendations)
        .merge(data, on='placeId')
        .sort_values('predicted_rating', ascending=False).drop_duplicates(subset=['title'])
    )   

# Display recommendations (show all at once instead of tabs)
if not st.session_state.recommendations.empty:
    st.write("Your Ratings Summary")
    df_rated_restaurants = pd.DataFrame(
        [(rest, rate) for rest, rate in st.session_state.rated_restaurants.items()],
        columns=['Restaurant', 'Your Rating']
    )
    st.dataframe(df_rated_restaurants)
    st.subheader("Top Restaurant Recommendations")

    # Display all top 5 recommendations together
    for i, (_, row) in enumerate(st.session_state.recommendations.iterrows()):
        # st.markdown(f"### {i+1}. {row['title']}")
        with st.expander(f"Restaurant #{i+1}: {row['title']}"):
            get_user_rating(row['title'], mode='display', idx=i)
            st.markdown(f"""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>
                <p style='color: black;'>Predicted Rating: ⭐ {row['predicted_rating']:.2f}</p>
                <p style='color: black;'>Average Score: ⭐ {row['totalScore']:.1f}</p>
            </div>
            """, unsafe_allow_html=True)       

# Reset button
if st.sidebar.button("Start Over"):
    st.session_state.rated_restaurants = {}
    st.session_state.restaurants_to_rate = []
    st.session_state.rating_completed = False
    st.session_state.recommendations = pd.DataFrame()
    st.session_state.temp_ratings = {}
    st.rerun()
