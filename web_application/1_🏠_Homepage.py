import streamlit as st

st.set_page_config(
    page_title="Restaurant Recommender System",
    page_icon="🍔",
)
st.write("# Restaurant Recommender System")
st.sidebar.success("Select a demo above.")

st.markdown("""            
            This is a Restaurant Recommender System. 
            You can rate restaurants and get recommendations based on your ratings.            
            """)

