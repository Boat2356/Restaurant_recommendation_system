import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ดึง API key จากไฟล์ secret.toml
# supabase_url = st.secrets["SUPABASE_URL"]
# supabase_key = st.secrets["SUPABASE_KEY"]

# supabase: Client = create_client(supabase_url, supabase_key)

# Page setup
st.set_page_config(
    page_title="🔍 Filter Restaurants",
    page_icon="🔍",
    layout="wide"
)
st.title("🔍 Filter Restaurants")
st.sidebar.success("Select your preferred filters")

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

# Load data
#data, ratings_data = load_data_from_db()
data, ratings_data = load_data()

# Initialize session state for filters if not exists
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = data

if 'apply_filters' not in st.session_state:
    st.session_state.apply_filters = False

# Create filter layout with tabs
filter_tabs = st.tabs(["Restaurant Type", "Location", "Price & Rating", "Additional Features"])

with filter_tabs[0]:
    st.subheader("Restaurant Type")
    # Get unique categories and sort them
    categories = sorted(data['categoryName'].dropna().unique())
    selected_categories = st.multiselect("Select Restaurant Categories:", categories)

with filter_tabs[1]:
    st.subheader("Location")
    # Get unique cities and sort them
    cities = sorted(data['city'].dropna().unique())
    selected_cities = st.multiselect("Select Cities:", cities)

with filter_tabs[2]:
    st.subheader("Price & Rating")
    
    # Price filter
    price_options = sorted(data['price'].dropna().unique())
    selected_prices = st.multiselect("Select Price Range:", price_options)
    
    # Rating filter with slider
    min_rating, max_rating = st.slider(
        "Select Rating Range:",
        min_value=1.0,
        max_value=5.0,
        value=(3.0, 5.0),
        step=0.1
    )

with filter_tabs[3]:
    st.subheader("Additional Features")
    
    # Get important additionalInfo fields
    # These are the key features we want to highlight
    
    important_features = [
        'delivery', 'dining_in', 'group_friendly', 
        'kid_friendly', 'free_parking', 
        'beer', 'alcohol', 'desserts', 
        'wheelchair_accessible', 'free_wifi',
        'credit_cards', 'halal_food', 'vegetarian_options',
        'live_performances', 'live_music', 'dog_friendly'
    ]
    important_features_map = {
        'delivery': 'บริการจัดส่ง',
        'dining_in': 'นั่งรับประทานที่ร้าน',
        'group_friendly': 'มาเป็นกลุ่ม',
        'kid_friendly': 'เหมาะสำหรับ',
        'free_parking': 'ที่จอดรถแบบไม่เสียค่าใช้จ่าย',
        'beer': 'เบียร์',
        'alcohol': 'แอลกอฮอล์',
        'desserts': 'ของหวาน',
        'wheelchair_accessible': 'ทางเข้าสำหรับเก้าอี้รถเข็น',
        'free_wifi': 'Wi-Fi ฟรี',
        'credit_cards': 'บัตรเครดิต',
        'halal_food': 'อาหารฮาลาล',
        'vegetarian_options': 'ตัวเลือกสำหรับมังสวิรัติ',
        'live_performances': 'การแสดงสด',
        'live_music': 'ดนตรีสด',
        'dog_friendly': 'ต้อนรับสุนัข'
    }
    
    # Create 4 columns for better layout
    col1, col2, col3, col4 = st.columns(4)
    selected_features = {}
    
    # Distribute features across columns
    columns = [col1, col2, col3, col4]
    features_per_column = len(important_features_map) // len(columns)
    
    for i, feature in enumerate(important_features_map):
        col_idx = i // features_per_column
        with columns[col_idx]:
            selected_features[feature] = st.checkbox(important_features_map[feature], value=False)


# Apply filters button
if st.button("Apply Filters"):
    st.session_state.apply_filters = True
    filtered = data.copy()
    
    # Apply category filter
    if selected_categories:
        filtered = filtered[filtered['categoryName'].isin(selected_categories)]
    
    # Apply city filter
    if selected_cities:
        filtered = filtered[filtered['city'].isin(selected_cities)]
    
    # Apply price filter
    if selected_prices:
        filtered = filtered[filtered['price'].isin(selected_prices)]
    
    # Apply rating filter
    filtered = filtered[(filtered['totalScore'] >= min_rating) & (filtered['totalScore'] <= max_rating)]
    
    # Apply additional features filters
    for feature, selected in selected_features.items():
        if selected:
            # Check if additionalInfo contains the feature with value True
            # The additionalInfo is stored as a string representation of a dictionary
            # ตรวจสอบว่าคอลัมน์มีอยู่ในข้อมูลก่อน
            if feature in filtered.columns:
                filtered = filtered[filtered[feature] == True]
    
    # Update filtered data in session state
    st.session_state.filtered_data = filtered        

if st.button("Reset Filters"):
    st.session_state.filtered_data = data
    st.session_state.apply_filters = False
    st.success("Filters have been reset.")

# Display results
if st.session_state.apply_filters:
    # Count restaurants after filtering
    count = len(st.session_state.filtered_data['placeId'].unique())
    
    st.subheader(f"Filtered Results: {count} Restaurants")
    
    if count == 0:
        st.warning("No restaurants match your selected filters. Please try different criteria.")
    else:
        # Show sample of filtered restaurants
        st.dataframe(
            st.session_state.filtered_data[['title', 'categoryName', 'city', 'price', 'totalScore']].drop_duplicates().reset_index(drop=True),
            use_container_width=True
        )
        
        # Save filtered results for use in recommendation page
        #if st.button("Use These Filters for Recommendations"):
            # Store unique place IDs of filtered restaurants
        filtered_ids = st.session_state.filtered_data['placeId'].unique().tolist()
        # Save to session state for use in the recommendation page
        st.session_state.filtered_restaurant_ids = filtered_ids
        st.success(f"Filter applied! {count} restaurants will be used for recommendations on the Projects page.")
else:
    st.info("Use the filters above to narrow down restaurant options, then click 'Apply Filters'.")


    
# Add explanation
st.markdown("""
### How to Use
1. Select your preferred filters from each tab
2. Click 'Apply Filters' to see matching restaurants
3. Click 'Use These Filters for Recommendations' to use these restaurants for the recommendation system
4. Go to the 'Projects' page to get personalized recommendations

The recommendation system will only use restaurants from your filtered selection to provide more relevant suggestions.
""")