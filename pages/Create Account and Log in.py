import re

import streamlit as st

from storage import authenticate, list_example_profiles, register, signup_code, start_demo

st.set_page_config(page_title="FIRE Calculator - Login", page_icon="🔒")

# Streamlit UI
st.title('FireSight App')

# Authentication State
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# Login Page
if not st.session_state['logged_in']:
    st.header('Try a demo profile')
    st.write("Jump straight in with a ready-made household. Edits stay in your browser session.")
    examples = list_example_profiles()
    cols = st.columns(len(examples))
    for col, (slug, example) in zip(cols, examples.items()):
        with col:
            st.subheader(example["title"])
            st.caption(example["summary"])
            if st.button("Use this profile", key=f"demo_{slug}"):
                start_demo(slug)
                st.rerun()

    st.header('Login')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        user_id = authenticate(email, password)
        if user_id:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user_id
            st.success('Logged in successfully')
            st.rerun()
        else:
            st.error('Invalid email or password')

    st.header('Create Account')
    required_code = signup_code()
    new_email = st.text_input('New Email')
    new_password = st.text_input('New Password', type='password')
    beta_code = st.text_input('Beta Code') if required_code else None
    if st.button('Create Account'):
        if not new_email or not new_password:
            st.error('Email and password are required')
        #regex check email
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            st.error('Invalid email')
        elif required_code and beta_code != required_code:
            st.error('Invalid beta code')
        else:
            try:
                user_id = register(new_email, new_password)
            except ValueError as e:
                st.error(str(e))
            else:
                st.success('Account created successfully. You are now logged in.')
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user_id
                st.rerun()
else:
    st.header('Welcome!')
    if str(st.session_state['user_id']).startswith("demo:"):
        st.write('You are exploring a demo profile.')
    else:
        st.write('You are logged in.')
    st.page_link("pages/Edit Profile.py", label="Edit your profile", icon="✏️")
    st.page_link("pages/Run Simulation.py", label="Run the simulation", icon="🔥")
    st.page_link("pages/Scenario Analysis.py", label="Compare scenarios", icon="🔍")

    if st.button('Logout'):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.rerun()
