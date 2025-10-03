import json
import os

import requests
import streamlit as st
from dotenv import load_dotenv

# -------------------------
# Configuration
# -------------------------
# Change this if your FastAPI backend runs on a different host/port
load_dotenv()
BASE_URL = os.getenv("BASE_URL")

# Endpoints (as you described)
LOGIN_ENDPOINT = f"{BASE_URL}/auth/login"
REGISTER_ENDPOINT = f"{BASE_URL}/auth/register"
BLOG_LIST_ENDPOINT = f"{BASE_URL}/blogs/blog-list"
BLOG_CREATE_ENDPOINT = f"{BASE_URL}/blogs/blog"
BLOG_DETAIL_ENDPOINT = f"{BASE_URL}/blogs/blog/{{id}}"  # format with id
SUGGEST_ENDPOINT = f"{BASE_URL}/llm/suggest-topics"

# -------------------------
# Helpers for API calls
# -------------------------

def get_auth_headers():
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


def api_post(url: str, payload: dict, auth: bool = False):
    headers = get_auth_headers() if auth else {"Content-Type": "application/json"}
    return requests.post(url, headers=headers, json=payload)


def api_get(url: str, auth: bool = False):
    headers = get_auth_headers() if auth else {"Content-Type": "application/json"}
    return requests.get(url, headers=headers)


def api_put(url: str, payload: dict, auth: bool = True):
    headers = get_auth_headers()
    return requests.put(url, headers=headers, json=payload)


def api_delete(url: str, auth: bool = True):
    headers = get_auth_headers()
    return requests.delete(url, headers=headers)


# -------------------------
# Session state defaults
# -------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"


# -------------------------
# UI Pages
# -------------------------

def login_page():
    st.title("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        payload = {"email": email, "password": password}
        try:
            resp = api_post(LOGIN_ENDPOINT, payload, auth=False)
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to backend. Is FastAPI running at {}?".format(BASE_URL))
            return
        if resp.status_code in (200, 201):
            body = resp.json()
            results = body.get("results") or body
            if isinstance(results, dict):
                st.session_state.access_token = results.get("access_token")
                st.session_state.refresh_token = results.get("refresh_token")
                st.session_state.user = results.get("user")
                st.success("Login successful")
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Unexpected login response format")
        else:
            try:
                st.error(resp.json().get("message") or f"Login failed ({resp.status_code})")
            except Exception:
                st.error(f"Login failed: {resp.status_code}")

    st.write("---")
    st.write("If you don't have an account, register below.")
    with st.expander("Register"):
        with st.form("register_form"):
            r_email = st.text_input("Email", key="r_email")
            r_password = st.text_input("Password", type="password", key="r_password")
            r_first = st.text_input("First name", key="r_first")
            r_last = st.text_input("Last name", key="r_last")
            r_sub = st.form_submit_button("Register")
        if r_sub:
            payload = {
                "email": r_email,
                "password": r_password,
                "first_name": r_first,
                "last_name": r_last,
            }
            try:
                resp = api_post(REGISTER_ENDPOINT, payload, auth=False)
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to backend for registration.")
                return
            if resp.status_code in (200, 201):
                st.success("Registered successfully — please login.")
            else:
                try:
                    st.error(resp.json().get("message") or f"Registration failed ({resp.status_code})")
                except Exception:
                    st.error(f"Registration failed: {resp.status_code}")



def logout():
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
    st.session_state.page = "login"
    st.success("Logged out")
    st.rerun()


def dashboard_page():
    st.title("Dashboard")
    st.write(f"Logged in as: {st.session_state.user.get('email') if st.session_state.user else 'Unknown'}")
    if st.button("Logout"):
        logout()
        return
    st.write("\n")
    st.write("Use the sidebar to navigate: Blogs and Suggestions")


# Blogs page: list, view, create, edit, delete

def blogs_page():
    st.title("Blogs")

    # Show new blog form
    if st.session_state.get("show_new") is None:
        st.session_state.show_new = False

    cols = st.columns([3, 1])
    with cols[1]:
        if st.button("New Blog"):
            st.session_state.show_new = True

    # Create new blog
    if st.session_state.show_new:
        with st.form("create_blog"):
            title = st.text_input("Title", key="new_title")
            content = st.text_area("Content", key="new_content")
            submitted = st.form_submit_button("Create")
        if submitted:
            payload = {"title": title, "content": content}
            resp = api_post(BLOG_CREATE_ENDPOINT, payload, auth=True)
            if resp.status_code in (200, 201):
                st.success("Blog created")
                st.session_state.show_new = False
                st.experimental_rerun()
            else:
                try:
                    st.error(resp.json().get("message") or f"Create failed ({resp.status_code})")
                except Exception:
                    st.error(f"Create failed: {resp.status_code}")

    # Fetch blogs
    resp = api_get(BLOG_LIST_ENDPOINT, auth=True)
    if resp.status_code != 200:
        st.error(f"Could not fetch blogs: {resp.status_code}")
        return

    body = resp.json()
    results = body.get("results") if isinstance(body, dict) else body
    if not results:
        st.info("No blogs yet.")
        return

    # --- Grid layout ---
    st.markdown('<div class="blog-grid">', unsafe_allow_html=True)
    for blog in results:
        with st.container():
            st.markdown(f'''
            <div class="blog-card">
                <h3>{blog.get("title")}</h3>
                <div class="meta">By User {blog.get("user_id")}</div>
                <div>{blog.get("content")[:150]}{'...' if len(blog.get("content")) > 150 else ''}</div>
            </div>
            ''', unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 1])
            if c1.button("View", key=f"view_{blog.get('id')}"):
                st.session_state.selected_blog_id = blog.get('id')
                st.session_state.page = "blog_detail"
                st.rerun()
            if c2.button("Edit", key=f"edit_{blog.get('id')}"):
                st.session_state.edit_blog = blog
                st.session_state.page = "edit_blog"
                st.rerun()
            if c3.button("Delete", key=f"del_{blog.get('id')}"):
                confirm = st.confirm(f"Delete blog '{blog.get('title')}'?")
                if confirm:
                    del_resp = api_delete(BLOG_DETAIL_ENDPOINT.format(id=blog.get('id')), auth=True)
                    if del_resp.status_code in (200, 204):
                        st.success("Deleted")
                        st.rerun()
                    else:
                        try:
                            st.error(del_resp.json().get('message') or f"Delete failed ({del_resp.status_code})")
                        except Exception:
                            st.error(f"Delete failed: {del_resp.status_code}")
    st.markdown('</div>', unsafe_allow_html=True)

# Blog detail page

def blog_detail_page():
    blog_id = st.session_state.get('selected_blog_id')
    if not blog_id:
        st.error("No blog selected.")
        st.session_state.page = "blogs"
        return
    resp = api_get(BLOG_DETAIL_ENDPOINT.format(id=blog_id), auth=True)
    if resp.status_code == 200:
        body = resp.json()
        blog = body.get('results') if isinstance(body, dict) else body
        st.title(blog.get('title'))
        st.write(blog.get('content'))
        st.write(f"Created: {blog.get('created_at')}")
        if st.button("Back to blogs"):
            st.session_state.page = "blogs"
            st.rerun()
    else:
        st.error(f"Failed to load blog: {resp.status_code}")


# Edit blog page

def edit_blog_page():
    blog = st.session_state.get('edit_blog')
    if not blog:
        st.error("No blog selected for editing.")
        st.session_state.page = "blogs"
        return
    st.title("Edit Blog")
    with st.form("edit_form"):
        title = st.text_input("Title", value=blog.get('title'))
        content = st.text_area("Content", value=blog.get('content'))
        submitted = st.form_submit_button("Save")
    if submitted:
        payload = {"title": title, "content": content}
        resp = api_put(BLOG_DETAIL_ENDPOINT.format(id=blog.get('id')), payload, auth=True)
        if resp.status_code in (200, 201):
            st.success("Updated successfully")
            st.session_state.page = "blogs"
            st.rerun()
        else:
            try:
                st.error(resp.json().get('message') or f"Update failed ({resp.status_code})")
            except Exception:
                st.error(f"Update failed: {resp.status_code}")


# Suggestions page

def suggestions_page():
    st.title("Topic Suggestions")
    st.write("Enter a list of keywords (comma-separated), e.g. `python, fastapi, auth`")
    keywords = st.text_input("Keywords")
    if st.button("Suggest Topics"):
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        if not kw_list:
            st.error("Add at least one keyword")
            return
        payload = {"topics": kw_list}
        resp = api_post(SUGGEST_ENDPOINT, payload, auth=True)
        if resp.status_code == 200:
            body = resp.json()
            results = body.get('results') if isinstance(body, dict) else body
            # sometimes backend returns a JSON string
            try:
                if isinstance(results, str):
                    parsed = json.loads(results)
                else:
                    parsed = results
            except Exception:
                parsed = results
            if isinstance(parsed, list):
                for item in parsed:
                    st.subheader(item.get('topic'))
                    for p in item.get('points', []):
                        st.write(f"- {p}")
            else:
                st.write(parsed)
        else:
            st.error(f"Suggestion API failed: {resp.status_code}")


# -------------------------
# Navigation & app runner
# -------------------------

def run_app():
    st.sidebar.title("Navigation")
    if st.session_state.access_token:
        nav = st.sidebar.radio("Go to", ["dashboard", "blogs", "suggestions"], index=["dashboard", "blogs", "suggestions"].index(st.session_state.page) if st.session_state.page in ["dashboard","blogs","suggestions"] else 0)
        if st.sidebar.button("Logout"):
            logout()
    else:
        nav = st.sidebar.radio("Go to", ["login"])

    st.session_state.page = nav

    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "dashboard":
        dashboard_page()
    elif st.session_state.page == "blogs":
        if not st.session_state.access_token:
            st.warning("Please login first")
            st.session_state.page = "login"
            st.rerun()
        blogs_page()
    elif st.session_state.page == "blog_detail":
        blog_detail_page()
    elif st.session_state.page == "edit_blog":
        edit_blog_page()
    elif st.session_state.page == "suggestions":
        if not st.session_state.access_token:
            st.warning("Please login first")
            st.session_state.page = "login"
            st.rerun()
        suggestions_page()


if __name__ == "__main__":
    st.set_page_config(page_title="Blog Frontend", layout="wide")
    st.markdown(
        """
        <style>
        body, .css-1d391kg { font-family: 'Poppins', sans-serif; }
        .blog-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }
        .blog-card {
            background-color: #fefcfb;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .blog-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 25px rgba(0,0,0,0.15);
        }
        .blog-card h3 { color: #333; margin-bottom: 0.5rem; }
        .blog-card .meta { font-size: 0.85rem; color: #777; margin-bottom: 0.8rem; }
        </style>
        """,
        unsafe_allow_html=True
    )

    run_app()
