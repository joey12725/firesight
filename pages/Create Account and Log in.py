import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
import uuid
import hashlib

# DynamoDB configuration
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table('firesight-users')

st.set_page_config(page_title="FIRE Calculator - Login", page_icon="🔒")
# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, subscription_status, profile):
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(password)
    table.put_item(
        Item={
            'userid': user_id,
            'email': email,
            'password': hashed_password,
            'subscription_status': subscription_status,
            'profile': profile
        }
    )
    return user_id

def get_user(email, password):
    hashed_password = hash_password(password)
    response = table.query(
        IndexName='email-index',
        KeyConditionExpression=Key('email').eq(email)
    )
    items = response.get('Items', [])
    if items and items[0]['password'] == hashed_password:
        return items[0]
    return None

# Streamlit UI
st.title('FireSight App')

# Authentication State
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# Login Page
if not st.session_state['logged_in']:
    st.header('Login')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        user = get_user(email, password)
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user['userid']
            st.success('Logged in successfully')
        else:
            st.error('Invalid email or password')

    st.header('Create Account')
    new_email = st.text_input('New Email')
    new_password = st.text_input('New Password', type='password')
    beta_code = st.text_input('Beta Code')
    if st.button('Create Account'):
        if beta_code == 'friends-and-family':
            user_id = create_user(new_email, new_password, True, '{}')
            st.success(f'Account created successfully. Your user ID is {user_id}. Please login.')
        else:
            st.error('Invalid beta code')
else:
    st.header('Welcome!')
    st.write('You are logged in.')

    if st.button('Logout'):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.success('Logged out successfully')
