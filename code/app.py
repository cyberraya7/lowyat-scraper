import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import time
import pandas as pd
import streamlit as st

# Base URL for the forum topics
base_url = "https://forum.lowyat.net/topic/"

# Function to scrape data from a given topic ID and handle pagination dynamically
def scrape_forum_topic(topic_id):
    current_page_url = base_url + topic_id  # Start with the base URL for the topic ID
    all_data = []  # List to hold all scraped data

    while current_page_url:
        print(f"Scraping URL: {current_page_url}")
        
        # Fetch the current page
        response = requests.get(current_page_url)
        
        # Check if the request was successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract the title, time, usernames, and comments sections
            title_tags = soup.find_all("div", class_="maintitle")
            time_tags = soup.find_all("span", class_="postdetails")
            detail_tags = soup.find_all("div", class_="avatar_extra")
            user_tags = soup.find_all("span", class_="normalname")
            comment_tags = soup.find_all("div", class_="postcolor post_text")
            
            # Get the title of the page
            title = title_tags[0].find("b").get_text() if title_tags and title_tags[0].find("b") else "No Title"

            # List to hold structured data for all members
            members_data = []

            # Extract member information and add to members_data
            for tag in detail_tags:
                lines = tag.get_text(separator="\n").strip().split('\n')
                member_info = {}
                if len(lines) >= 8:  # Ensure there are enough lines to extract
                    member_info['member_type'] = lines[0].strip()
                    member_info['total_posts'] = lines[2].strip()
                    member_info['register'] = lines[7].strip()
                members_data.append(member_info)

            # Extract time, usernames, and comments
            times = [format_time(tag.get_text().splitlines()[0].strip()) for tag in time_tags]
            usernames = [tag.get_text() for tag in user_tags]
            comments = [tag.get_text() for tag in comment_tags]

            # Pair comments with usernames, time, title, and member details
            paired_comments = [{"title": title, "timestamp": time_item,
                                "member_info": members_data[index] if index < len(members_data) else {},
                                "username": username, "comment": comment_item} 
                               for index, (time_item, username, comment_item) in enumerate(zip(times, usernames, comments))]

            # Append the data for this page to the all_data list
            all_data.extend(paired_comments)

            # Try to find the "Next page" link
            pagelinks = soup.find_all("span", class_="pagelink")
            next_page_link = None
            for pagelink in pagelinks:
                a_tag = pagelink.find("a", title="Next page")
                if a_tag:
                    next_page_link = a_tag
                    break
            
            if next_page_link:
                # Construct the full URL for the next page
                current_page_url = "https://forum.lowyat.net" + next_page_link['href']
                print(f"Navigating to next page: {current_page_url}")
                time.sleep(10)  # Pause to avoid overwhelming the server
            else:
                # If there is no next page link, stop pagination
                print("No more pages to navigate.")
                break
        else:
            print(f"Failed to retrieve page: {response.status_code}")
            break
    
    return all_data

# Function to parse and format time
def format_time(raw_time):
    try:
        if not raw_time.strip():
            return "-"

        if "Yesterday" in raw_time:
            date = datetime.now().date() - timedelta(days=1)
            time_part = raw_time.split(",")[1].strip()
        elif "Today" in raw_time:
            date = datetime.now().date()
            time_part = raw_time.split(",")[1].strip()
        else:
            date_str, time_part = raw_time.split(",")
            date = datetime.strptime(date_str.strip(), "%d %b %Y").date()
        
        datetime_obj = datetime.strptime(f"{date} {time_part}", "%Y-%m-%d %I:%M %p")
        return datetime_obj.strftime("%d/%m/%Y@%I:%M %p")
    except Exception as e:
        print(f"Error parsing time: {raw_time}, Error: {e}")
        return "Unknown Date"

# Streamlit web app interface
st.title("Lowyat Forum Scraper")
st.markdown("#### Enter a Lowyat Forum Kopitiam Topic ID to scrape data")
st.markdown("#### Download data in JSON or CSV format.")

# Add an image below the instruction text
st.image("lowyat.jpeg", caption="Kopitiam Topic ID", width=500)

# Input field for topic ID
topic_id = st.text_input("Enter Topic ID:")

if st.button("Scrape Data"):
    if topic_id:
        with st.spinner("Scraping data..."):
            scraped_data = scrape_forum_topic(topic_id)
        
        if scraped_data:
            # Display data and allow download
            st.success("Data scraped successfully!")
            df = pd.DataFrame(scraped_data)
            st.write(df)

            # JSON download
            json_data = json.dumps(scraped_data, ensure_ascii=False, indent=4)
            st.download_button("Download JSON", json_data, file_name=f"{topic_id}.json", mime="application/json")
            
            # CSV download
            csv_data = df.to_csv(index=False)
            st.download_button("Download CSV", csv_data, file_name=f"{topic_id}.csv", mime="text/csv")
        else:
            st.error("No data found for this topic ID.")
    else:
        st.warning("Please enter a valid Topic ID.")
