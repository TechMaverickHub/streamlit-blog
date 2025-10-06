import base64
import json
import os
import time
from typing import List, Dict, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

# -------------------------
# Configuration
# -------------------------
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

LOGIN_ENDPOINT = f"{BASE_URL}/auth/login"
REGISTER_ENDPOINT = f"{BASE_URL}/auth/register"
BLOG_LIST_ENDPOINT = f"{BASE_URL}/blogs/blog-list"
BLOG_CREATE_ENDPOINT = f"{BASE_URL}/blogs/blog"
BLOG_DETAIL_ENDPOINT = f"{BASE_URL}/blogs/blog/{{id}}"
SUGGEST_ENDPOINT = f"{BASE_URL}/llm/suggest-topics"

# -------------------------
# Utility helpers
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
# App defaults & state
# -------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "show_new" not in st.session_state:
    st.session_state.show_new = False
if "theme" not in st.session_state:
    st.session_state.theme = "light"  # or 'dark'
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = {}

# -------------------------
# Branding assets (inline small svg favicon + logo)
# -------------------------
LOGO_SVG = '''<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'>
  <rect rx='20' width='120' height='120' fill='var(--accent)'></rect>
  <circle cx='60' cy='48' r='20' fill='white' opacity='0.95'></circle>
  <path d='M40 80c10-14 40-14 50 0' stroke='white' stroke-width='6' stroke-linecap='round' fill='none'></path>
</svg>'''

# data URL for page icon (small svg)
PAGE_ICON = "data:image/svg+xml;utf8," + LOGO_SVG.replace('\n', '')

# Color palette (CSS variables)
PALETTE = {
    "--bg": "#fbfbfc",
    "--card": "#ffffff",
    "--muted": "#6b7280",
    "--text": "#0f172a",
    "--accent": "#7c3aed",  # violet
    "--accent-2": "#06b6d4",
    "--glass": "rgba(255,255,255,0.6)",
}

DARK_PALETTE = {
    "--bg": "#0b1220",
    "--card": "#071025",
    "--muted": "#9aa4b2",
    "--text": "#e6eef6",
    "--accent": "#8b5cf6",
    "--accent-2": "#06b6d4",
    "--glass": "rgba(255,255,255,0.03)",
}

# -------------------------
# Styling (custom CSS)
# -------------------------
GLOBAL_STYLE = """
:root {
  --topbar-height: 64px;
}

/* theme variables (will be injected dynamically) */

.app-topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--topbar-height);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; z-index: 9999;
  backdrop-filter: blur(6px);
  box-shadow: 0 2px 12px rgba(2,6,23,0.12);
}

.brand { display:flex; gap:12px; align-items:center; }
.brand .logo {
  width: 40px;
  height: 40px;
  object-fit: contain;
  border-radius: 6px;
  margin-right: 8px;
  display: inline-block;
}

.brand h1 { font-size:18px; margin:0; }

.nav-links { display:flex; gap:12px; align-items:center; }
.nav-links a { text-decoration:none; padding:8px 12px; border-radius:8px; }
.nav-links a.active { background: linear-gradient(90deg,var(--accent),var(--accent-2)); color: white; }

.main-container { padding: calc(var(--topbar-height) + 28px) 36px 48px 36px; }

.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:20px; }
.card {
  background: var(--card);
  border-radius: 12px; padding: 16px; box-shadow: 0 6px 18px rgba(2,6,23,0.06);
  transition: transform .18s ease, box-shadow .18s ease; overflow:hidden;
}
.card:hover { transform: translateY(-6px); box-shadow: 0 18px 30px rgba(2,6,23,0.08); }
.card .thumb { width:100%; height:160px; border-radius:8px; object-fit:cover; margin-bottom:12px; }
.meta { color: var(--muted); font-size:13px; }
.card-title { font-size:16px; margin:0 0 8px 0; color:var(--text);} 
.card-excerpt { color:var(--muted); font-size:14px; }

/* modal */
.modal-backdrop{ position:fixed; inset:0; background: rgba(2,6,23,0.45); display:flex; align-items:center; justify-content:center; z-index:99999; }
.modal { background:var(--card); padding:18px; border-radius:12px; width:min(680px,94%); box-shadow:0 20px 60px rgba(2,6,23,0.3); }

/* reading layout */
.reader { max-width: 860px; margin: 0 auto; background:transparent; }
.reader h1 { font-size:36px; margin-bottom:8px; }
.reader .meta { margin-bottom:18px; }
.reader .content { font-size:18px; line-height:1.7; color:var(--text); background:var(--glass); padding:24px; border-radius:8px; }

/* footer */
.app-footer { text-align:center; padding:28px; color:var(--muted); font-size:14px; }

/* skeleton */
.skel { background: linear-gradient(90deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); border-radius:8px; }
.skel-thumb { height:140px; width:100%; }
.skel-line{ height:14px; margin:8px 0; width:100%; }

/* responsive tweaks */
@media (max-width:760px){ .brand h1{ display:none; } .nav-links{ display:none; } }
"""

# -------------------------
# UI building blocks
# -------------------------

def inject_style(theme: str = "light"):
    palette = PALETTE if theme == "light" else DARK_PALETTE
    css_vars = "\n".join([f"{k}: {v};" for k, v in palette.items()])
    full = f"<style>:root {{ {css_vars} }} {GLOBAL_STYLE}</style>"
    st.markdown(full, unsafe_allow_html=True)


def render_topbar():
    # topbar layout using columns to keep alignment consistent
    cols = st.columns([1, 6, 2])
    with cols[0]:
        st.markdown(f"<div class='brand'>"
                    f"<div class='logo'>{LOGO_SVG}</div>"
                    f"<h1 style='margin:0;'>FluxBlog</h1>"
                    f"</div>", unsafe_allow_html=True)
    with cols[1]:
        links_html = ""
        for p, label in [("dashboard", "Home"), ("blogs", "Blogs"), ("suggestions", "Suggest")]:
            active = "active" if st.session_state.page == p else ""
            links_html += f"<a class='{active}' href='#{p}' onclick=\"window.dispatchEvent(new CustomEvent('nav',{ '{' }detail: '{p}'{ '}' }))\">{label}</a>"
        st.markdown(f"<div class='nav-links'>{links_html}</div>", unsafe_allow_html=True)
    with cols[2]:
        # theme toggle + user
        theme = st.session_state.theme
        if st.button("Toggle Theme"):
            st.session_state.theme = "dark" if theme == "light" else "light"
            st.rerun()
        if st.session_state.access_token:
            st.markdown(f"<div style='text-align:right; font-size:14px;'>Signed in as <b>{st.session_state.user.get('email') if st.session_state.user else 'You'}</b></div>", unsafe_allow_html=True)


# Navigation listener (small script to map hash clicks to Streamlit radio)
NAV_SCRIPT = """
<script>
window.addEventListener('nav', (e)=>{
  const page = e.detail;
  const el = window.parent.document.querySelector('textarea[data-testid="stSessionState"]');
  // fallback: use URL hash
  window.location.hash = page;
});
</script>
"""

# -------------------------
# Pages
# -------------------------

def login_page():
    st.title("Welcome — Login")
    with st.form('login'):
        email = st.text_input('Email')
        password = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Login')
    if submitted:
        payload = {"email": email, "password": password}
        try:
            with st.spinner('Authenticating...'):
                print("Logging in with payload:", payload)
                print("Using LOGIN_ENDPOINT:", LOGIN_ENDPOINT)
                resp = api_post(LOGIN_ENDPOINT, payload, auth=False)
        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to backend at {BASE_URL}")
            return
        if resp.status_code in (200, 201):
            body = resp.json()
            results = body.get('results') or body
            if isinstance(results, dict):
                st.session_state.access_token = results.get('access_token')
                st.session_state.refresh_token = results.get('refresh_token')
                st.session_state.user = results.get('user')
                st.success('Login successful')
                st.session_state.page = 'dashboard'
                st.rerun()
            else:
                st.error('Unexpected login response format')
        else:
            try:
                st.error(resp.json().get('message') or f'Login failed ({resp.status_code})')
            except Exception:
                st.error(f'Login failed: {resp.status_code}')

    st.markdown('---')
    with st.expander('Register'):
        with st.form('register'):
            r_email = st.text_input('Email', key='r_email')
            r_password = st.text_input('Password', type='password', key='r_password')
            r_first = st.text_input('First name', key='r_first')
            r_last = st.text_input('Last name', key='r_last')
            r_sub = st.form_submit_button('Register')
        if r_sub:
            payload = {"email": r_email, "password": r_password, "first_name": r_first, "last_name": r_last}
            try:
                resp = api_post(REGISTER_ENDPOINT, payload, auth=False)
            except requests.exceptions.ConnectionError:
                st.error('Could not connect to backend for registration.')
                return
            if resp.status_code in (200, 201):
                st.success('Registered successfully — please login.')
            else:
                try:
                    st.error(resp.json().get('message') or f'Registration failed ({resp.status_code})')
                except Exception:
                    st.error(f'Registration failed: {resp.status_code}')


def dashboard_page():
    st.title('Dashboard')
    st.write('Use the top navigation to go to Blogs or Suggestions')
    st.write('\n')
    if st.button('Logout'):
        logout()
        return


def fetch_blogs_with_loading() -> Optional[List[Dict]]:
    placeholder = st.empty()
    with placeholder.container():
        # skeleton grid
        placeholder.markdown('<div class="grid">', unsafe_allow_html=True)
        for _ in range(3):
            placeholder.markdown('<div class="card skel">'
                                 '<div class="skel-thumb"></div>'
                                 '<div class="skel-line"></div>'
                                 '<div class="skel-line" style="width:80%"></div>'
                                 '</div>', unsafe_allow_html=True)
        placeholder.markdown('</div>', unsafe_allow_html=True)
    try:
        time.sleep(0.6)  # small demo delay
        resp = api_get(BLOG_LIST_ENDPOINT, auth=True)
    finally:
        placeholder.empty()

    if resp.status_code != 200:
        st.error(f'Could not fetch blogs: {resp.status_code}')
        return None
    body = resp.json()
    results = body.get('results') if isinstance(body, dict) else body
    return results


def blogs_page():
    st.title('Blogs')

    cols = st.columns([3, 1])
    with cols[1]:
        if st.button('New Blog'):
            st.session_state.show_new = True

    if st.session_state.show_new:
        with st.form('create_blog'):
            title = st.text_input('Title', key='new_title')
            content = st.text_area('Content', key='new_content')
            submitted = st.form_submit_button('Create')
        if submitted:
            payload = {'title': title, 'content': content}
            with st.spinner('Creating...'):
                resp = api_post(BLOG_CREATE_ENDPOINT, payload, auth=True)
            if resp.status_code in (200, 201):
                st.success('Blog created')
                st.session_state.show_new = False
                st.rerun()
            else:
                try:
                    st.error(resp.json().get('message') or f'Create failed ({resp.status_code})')
                except Exception:
                    st.error(f'Create failed: {resp.status_code}')

    results = fetch_blogs_with_loading()
    if results is None:
        return
    if not results:
        st.info('No blogs yet.')
        return

    st.markdown('<div class="grid">', unsafe_allow_html=True)
    for blog in results:
        blog_id = blog.get('id')
        thumb = blog.get('thumbnail_url') or placeholder_image_data_url(blog.get('title'))
        st.markdown(f"<div class='card'>"
                    f"<img class='thumb' src='{thumb}' alt='thumb' />"
                    f"<div class='meta'>By user {blog.get('user_id')}</div>"
                    f"<h3 class='card-title'>{blog.get('title')}</h3>"
                    f"<div class='card-excerpt'>{(blog.get('content') or '')[:160]}{ '...' if (blog.get('content') or '')|len > 160 else ''}</div>"
                    f"</div>", unsafe_allow_html=True)

        # buttons (workaround because we can't attach buttons inside raw HTML reliably)
        cols = st.columns([1, 1, 1])
        with cols[0]:
            if st.button('View', key=f'view_{blog_id}'):
                st.session_state.selected_blog_id = blog_id
                st.session_state.page = 'blog_detail'
                st.rerun()
        with cols[1]:
            if st.button('Edit', key=f'edit_{blog_id}'):
                st.session_state.edit_blog = blog
                st.session_state.page = 'edit_blog'
                st.rerun()
        with cols[2]:
            if st.button('Delete', key=f'delete_{blog_id}'):
                st.session_state.confirm_delete[blog_id] = True
        # confirm modal
        if st.session_state.confirm_delete.get(blog_id):
            show_confirm_delete_modal(blog_id)

    st.markdown('</div>', unsafe_allow_html=True)


def show_confirm_delete_modal(blog_id):
    st.markdown('<div class="modal-backdrop">', unsafe_allow_html=True)
    st.markdown('<div class="modal">', unsafe_allow_html=True)
    st.write('Are you sure you want to delete this blog? This action is irreversible.')
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button('Confirm Delete', key=f'confirm_del_{blog_id}'):
            resp = api_delete(BLOG_DETAIL_ENDPOINT.format(id=blog_id), auth=True)
            if resp.status_code in (200, 204):
                st.success('Deleted')
                st.session_state.confirm_delete.pop(blog_id, None)
                st.rerun()
            else:
                st.error(f'Delete failed: {resp.status_code}')
                st.session_state.confirm_delete.pop(blog_id, None)
    with c2:
        if st.button('Cancel', key=f'cancel_del_{blog_id}'):
            st.session_state.confirm_delete.pop(blog_id, None)
    st.markdown('</div></div>', unsafe_allow_html=True)


def blog_detail_page():
    blog_id = st.session_state.get('selected_blog_id')
    if not blog_id:
        st.error('No blog selected.')
        st.session_state.page = 'blogs'
        return
    with st.spinner('Loading blog...'):
        resp = api_get(BLOG_DETAIL_ENDPOINT.format(id=blog_id), auth=True)
    if resp.status_code == 200:
        body = resp.json()
        blog = body.get('results') if isinstance(body, dict) else body
        st.markdown('<div class="reader">', unsafe_allow_html=True)
        st.markdown(f"<h1>{blog.get('title')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='meta'>By user {blog.get('user_id')} • {blog.get('created_at')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='content'>{st.experimental_get_query_params() or ''}</div>", unsafe_allow_html=True)
        # Use native markdown rendering for the content block
        st.markdown(blog.get('content') or '', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button('Back to blogs'):
            st.session_state.page = 'blogs'
            st.rerun()
    else:
        st.error(f'Failed to load blog: {resp.status_code}')


def edit_blog_page():
    blog = st.session_state.get('edit_blog')
    if not blog:
        st.error('No blog selected for editing.')
        st.session_state.page = 'blogs'
        return
    st.title('Edit Blog')
    with st.form('edit_form'):
        title = st.text_input('Title', value=blog.get('title'))
        content = st.text_area('Content', value=blog.get('content'))
        submitted = st.form_submit_button('Save')
    if submitted:
        payload = {'title': title, 'content': content}
        resp = api_put(BLOG_DETAIL_ENDPOINT.format(id=blog.get('id')), payload, auth=True)
        if resp.status_code in (200, 201):
            st.success('Updated successfully')
            st.session_state.page = 'blogs'
            st.rerun()
        else:
            try:
                st.error(resp.json().get('message') or f'Update failed ({resp.status_code})')
            except Exception:
                st.error(f'Update failed: {resp.status_code}')


def suggestions_page():
    st.title('Topic Suggestions')
    st.write('Enter a list of keywords (comma-separated), e.g. `python, fastapi, auth`')
    keywords = st.text_input('Keywords')
    if st.button('Suggest Topics'):
        kw_list = [k.strip() for k in keywords.split(',') if k.strip()]
        if not kw_list:
            st.error('Add at least one keyword')
            return
        payload = {'topics': kw_list}
        resp = api_post(SUGGEST_ENDPOINT, payload, auth=True)
        if resp.status_code == 200:
            body = resp.json()
            results = body.get('results') if isinstance(body, dict) else body
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
            st.error(f'Suggestion API failed: {resp.status_code}')


def logout():
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
    st.session_state.page = 'login'
    st.success('Logged out')
    st.rerun()


# Small helper to render a placeholder image as data URL (SVG)
def placeholder_image_data_url(text: str = '') -> str:
    safe = (text or 'cover').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='600'><rect width='100%' height='100%' fill='%23e9d5ff' /><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-size='48' fill='%23ffffff' font-family='Arial'>{safe}</text></svg>"
    return 'data:image/svg+xml;utf8,' + svg


# -------------------------
# Runner / Navigation
# -------------------------

st.set_page_config(page_title='FluxBlog', page_icon=PAGE_ICON, layout='wide')
inject_style(st.session_state.theme)

# topbar
render_topbar()
st.markdown(NAV_SCRIPT, unsafe_allow_html=True)

# main container
st.markdown('<div class="main-container">', unsafe_allow_html=True)

page = st.session_state.page
if page == 'login':
    login_page()
elif page == 'dashboard':
    if not st.session_state.access_token:
        st.warning('Please login first')
        st.session_state.page = 'login'
        st.rerun()
    dashboard_page()
elif page == 'blogs':
    if not st.session_state.access_token:
        st.warning('Please login first')
        st.session_state.page = 'login'
        st.rerun()
    blogs_page()
elif page == 'blog_detail':
    if not st.session_state.access_token:
        st.warning('Please login first')
        st.session_state.page = 'login'
        st.rerun()
    blog_detail_page()
elif page == 'edit_blog':
    edit_blog_page()
elif page == 'suggestions':
    if not st.session_state.access_token:
        st.warning('Please login first')
        st.session_state.page = 'login'
        st.rerun()
    suggestions_page()

st.markdown('</div>', unsafe_allow_html=True)

# footer
st.markdown('<div class="app-footer">Built with ❤️ — <a href="https://github.com/TechMaverickHub/flux-comic-stripgen" target="_blank">GitHub</a> | FluxBlog Demo</div>', unsafe_allow_html=True)
