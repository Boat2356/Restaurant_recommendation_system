import streamlit as st
import pandas as pd
import folium
from surprise import SVD, dump, Dataset, Reader
from collections import defaultdict
from streamlit_folium import st_folium
import time
from supabase import create_client, Client

# อ่านไฟล์ secret.toml
#secret_data = toml.load(".\secrets.toml")

# ดึง API key จากไฟล์ secret.toml
# supabase_url = st.secrets["SUPABASE_URL"]
# supabase_key = st.secrets["SUPABASE_KEY"]

# supabase: Client = create_client(supabase_url, supabase_key)

# Page setup
st.set_page_config(
    page_title="🍲 Choose by Category",
    page_icon="🍲",
    layout="wide"
)
st.title("🍲 Choose Restaurants by Category")
st.sidebar.success("Choose restaurants from your favorite categories")

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

# Utility function for displaying restaurant info
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
if 'category_restaurants' not in st.session_state:
    st.session_state.category_restaurants = []
if 'selected_restaurants' not in st.session_state:
    st.session_state.selected_restaurants = []
if 'ratings_by_category' not in st.session_state:
    st.session_state.ratings_by_category = {}
if 'rating_completed_category' not in st.session_state:
    st.session_state.rating_completed_category = False
if 'recommendations_by_category' not in st.session_state:
    st.session_state.recommendations_by_category = pd.DataFrame()
if 'temp_ratings_by_category' not in st.session_state:
    st.session_state.temp_ratings_by_category = {}

# Step 1: Category Selection
if not st.session_state.rating_completed_category and not st.session_state.selected_restaurants:
    st.subheader("Step 1: Select Restaurant Categories")
    
    # Get unique categories
    categories = data['categoryName'].dropna().unique()
    categories = sorted([cat for cat in categories if pd.notna(cat) and cat.strip() != ''])
    
    # Add 'All Categories' option
    categories = ['All Categories'] + list(categories)
    
    # Allow multiple category selection
    selected_categories = st.multiselect(
        "Choose restaurant categories:",
        categories,
        default=['All Categories']
    )
    
    # Filter restaurants based on selected categories
    filtered_data = data.copy()
    if selected_categories and 'All Categories' not in selected_categories:
        filtered_data = data[data['categoryName'].isin(selected_categories)]
    
    # Group restaurants by category for display
    category_restaurant_dict = {}
    
    if 'All Categories' in selected_categories:
        # If 'All Categories' selected, include all categories
        for category in categories:
            if category != 'All Categories':
                category_restaurants = filtered_data[filtered_data['categoryName'] == category]['title'].unique()
                if len(category_restaurants) > 0:
                    category_restaurant_dict[category] = category_restaurants
    else:
        # Only include selected categories
        for category in selected_categories:
            category_restaurants = filtered_data[filtered_data['categoryName'] == category]['title'].unique()
            if len(category_restaurants) > 0:
                category_restaurant_dict[category] = category_restaurants
    
    # Store the filtered data for the next step
    st.session_state.category_restaurant_dict = category_restaurant_dict  

# Step 2: Restaurant Selection from Categories
if not st.session_state.rating_completed_category and len(st.session_state.selected_restaurants) == 0:
    st.subheader("Step 2: Select Restaurants to Rate")
    
    # เพิ่มการตรวจสอบข้อมูลใน session state
    if not hasattr(st.session_state, 'category_restaurant_dict') or not st.session_state.category_restaurant_dict:
        st.error("No categories selected or data not loaded properly")
        st.stop()
    
    # แสดง debug message
    st.write(f"Found {len(st.session_state.category_restaurant_dict)} categories with restaurants")
    
    all_selected_restaurants = []  # Initialize the list to store selected restaurants

    # Check if 'All Categories' is selected
    if 'All Categories' in selected_categories:
        # Show all restaurants from all categories without dropdown selection
        all_restaurants = data['title'].unique()
        selected = st.multiselect(
            "Select restaurants from all categories:",
            all_restaurants,
            key="select_all"
        )
        all_selected_restaurants = selected  # Store selected restaurants

    else:
    # If specific categories are selected, combine restaurants from the selected categories
        combined_restaurants = []
        
        for category in selected_categories:
            # Get restaurants from each selected category
            category_restaurants = data[data['categoryName'] == category]['title'].unique()
            combined_restaurants.extend(category_restaurants)  # Combine them into one list
        
        # Remove duplicates (if any) after combining
        combined_restaurants = list(set(combined_restaurants))
        
        # Show the combined list of restaurants in one dropdown
        selected = st.multiselect(
            "Select restaurants from the selected categories:",
            combined_restaurants,
            key="select_combined"
        )
        all_selected_restaurants = selected  # Store selected restaurants
    
    # Show number of recommendations
    num_recommendations = st.slider("Number of recommendations to show:", 1, 10, 5)
    st.session_state.num_recommendations_category = num_recommendations
    
    # Button to proceed to the next step
    if st.button("Next: Rate Selected Restaurants", type="primary"):
        if not all_selected_restaurants:
            st.warning("Please select at least one restaurant.")
        else:
            st.session_state.selected_restaurants = all_selected_restaurants  # Update session state
            st.rerun()

# Step 3: Rate selected restaurants
if not st.session_state.rating_completed_category and st.session_state.selected_restaurants:
    st.subheader("Step 3: Rate Your Selected Restaurants")
    
    # แสดงจำนวนร้านที่ต้องให้คะแนน
    st.info(f"You need to rate {len(st.session_state.selected_restaurants)} selected restaurants.")
    
    # ใช้ Accordion เพื่อแสดงร้านอาหารแต่ละร้าน
    for i, restaurant_name in enumerate(st.session_state.selected_restaurants):
        with st.expander(f"Restaurant #{i+1}: {restaurant_name}", expanded=(i == 0)):
            rating = get_user_rating(restaurant_name, idx=i)
            if rating is not None:
                st.session_state.temp_ratings_by_category[restaurant_name] = rating
    
    # แสดงจำนวนร้านที่ได้รับการให้คะแนนแล้ว
    total_rated = len([r for r, rating in st.session_state.temp_ratings_by_category.items() if rating is not None])
    st.info(f"You have rated {total_rated}/{len(st.session_state.selected_restaurants)} restaurants.")
    
    # ปุ่มส่งคะแนนทั้งหมดพร้อมกัน
    if st.button("Submit All Ratings", type="primary"):
        # ดึงคะแนนจาก session state
        valid_ratings = {rest: rate for rest, rate in st.session_state.temp_ratings_by_category.items() if rate is not None}
        
        if not valid_ratings:
            st.warning("Please rate at least one restaurant before submitting.")
        else:
            # เพิ่มคะแนนที่ผู้ใช้ให้ไว้แล้ว
            st.session_state.ratings_by_category.update(valid_ratings)
            
            # ตรวจสอบว่าให้คะแนนครบทุกร้านที่เลือกหรือไม่
            if len(valid_ratings) == len(st.session_state.selected_restaurants):
                st.session_state.rating_completed_category = True
            
            st.rerun()

# Step 4: Generate recommendations based on ratings
if st.session_state.rating_completed_category and st.session_state.recommendations_by_category.empty:
    st.subheader("Step 4: Generating Recommendations")
    
    with st.spinner('Generating restaurant recommendations...'):
        time.sleep(3)
        
        # Create new user ratings dataset
        new_user_ratings = []
        for restaurant, rating in st.session_state.ratings_by_category.items():
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
                          for rest in st.session_state.ratings_by_category.keys()]
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
        st.session_state.recommendations_by_category = (
            recommendations_df
            .sort_values('predicted_rating', ascending=False)
            .head(st.session_state.num_recommendations_category)
            .merge(data, on='placeId')
            .sort_values('predicted_rating', ascending=False)
            .drop_duplicates(subset=['title'])
        )
        
        st.success("Recommendations generated successfully!")
        st.rerun()

# Step 5: Display recommendations with Accordion
if st.session_state.rating_completed_category and not st.session_state.recommendations_by_category.empty:
    st.write("Your Ratings Summary")
    df_rated_restaurants = pd.DataFrame(
        [(rest, rate) for rest, rate in st.session_state.ratings_by_category.items()],
        columns=['Restaurant', 'Your Rating']
    )
    st.dataframe(df_rated_restaurants)
    st.subheader("Top Restaurant Recommendations")

    # Display all top 5 recommendations in Accordion style
    for i, (_, row) in enumerate(st.session_state.recommendations_by_category.iterrows()):
        with st.expander(f"Restaurant #{i+1}: {row['title']}"):  # Set the first expander to expanded
            get_user_rating(row['title'], mode='display', idx=i)
            st.markdown(f"""
            <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px;'>
                <p style='color: black;'>Predicted Rating: ⭐ {row['predicted_rating']:.2f}</p>
                <p style='color: black;'>Average Score: ⭐ {row['totalScore']:.1f}</p>
            </div>
            """, unsafe_allow_html=True)


# Reset button
if st.sidebar.button("Start Over"):
    # Reset all session states related to this page
    st.session_state.category_restaurants = []
    st.session_state.selected_restaurants = []
    st.session_state.ratings_by_category = {}
    st.session_state.rating_completed_category = False
    st.session_state.recommendations_by_category = pd.DataFrame()
    st.session_state.temp_ratings_by_category = {}
    if hasattr(st.session_state, 'category_selection_done'):
        delattr(st.session_state, 'category_selection_done')
    if hasattr(st.session_state, 'category_restaurant_dict'):
        delattr(st.session_state, 'category_restaurant_dict')
    st.rerun()
