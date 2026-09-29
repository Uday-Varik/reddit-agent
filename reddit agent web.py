#!/usr/bin/env python3
"""
Reddit Agent Web Server - Mobile-friendly
Deploy this to Replit or similar cloud service
"""

from flask import Flask, render_template_string, request, jsonify, session
import praw
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = 'RedditAgent/1.0 (Mobile)'

# Global reddit instance
reddit = None

# HTML Template for Mobile Interface
MOBILE_INTERFACE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Auto-Post Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; padding: 10px; }
        .header { background: #ff4500; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .header p { font-size: 13px; opacity: 0.9; }
        .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; font-family: inherit; resize: vertical; min-height: 100px; }
        button { width: 100%; padding: 12px; background: #ff4500; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 10px; }
        button:active { opacity: 0.8; }
        .status { padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 14px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .loading { background: #d1ecf1; color: #0c5460; }
        .subreddit-item { background: #f9f9f9; padding: 12px; border-left: 4px solid #ff4500; margin: 10px 0; border-radius: 4px; }
        .subreddit-item h3 { color: #ff4500; margin-bottom: 5px; font-size: 15px; }
        .subreddit-item p { font-size: 13px; color: #666; margin: 5px 0; }
        .draft-box { background: #f0f0f0; padding: 12px; border-radius: 8px; margin: 10px 0; font-size: 13px; line-height: 1.5; max-height: 200px; overflow-y: auto; }
        .approve-btn { background: #28a745; }
        .auth-status { font-size: 13px; color: #666; }
        .auth-status.connected { color: #28a745; }
        .section-title { font-size: 16px; font-weight: 600; margin: 20px 0 10px; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Reddit Auto-Post Agent</h1>
            <p>Find subreddits and auto-post from your phone</p>
        </div>

        <!-- Authentication Status -->
        <div class="card">
            <div class="auth-status" id="authStatus">🔴 Not authenticated</div>
            <button id="authBtn" onclick="authenticate()">Connect Reddit Account</button>
        </div>

        <!-- Issue Input -->
        <div class="card" id="inputSection" style="display:none;">
            <h2 style="font-size: 18px; margin-bottom: 10px;">Describe Your Issue</h2>
            <textarea id="issueInput" placeholder="E.g., My laptop keeps overheating when gaming. What should I check?"></textarea>
            <button onclick="findSubreddits()">Find Subreddits & Draft Posts</button>
            <div id="inputStatus"></div>
        </div>

        <!-- Results Section -->
        <div id="resultsSection" style="display:none;">
            <div class="section-title">📍 Relevant Subreddits</div>
            <div id="subredditsList"></div>

            <div class="section-title">✏️ Drafted Posts</div>
            <div id="draftsList"></div>

            <button style="background: #6c757d; margin-top: 20px;" onclick="resetForm()">← Back</button>
        </div>

        <div id="statusMessage"></div>
    </div>

    <script>
        // Check auth status on load
        window.onload = () => checkAuthStatus();

        function checkAuthStatus() {
            fetch('/api/auth-status')
                .then(r => r.json())
                .then(data => {
                    const statusEl = document.getElementById('authStatus');
                    const inputSection = document.getElementById('inputSection');
                    const authBtn = document.getElementById('authBtn');
                    
                    if (data.authenticated) {
                        statusEl.textContent = '🟢 Connected as ' + data.username;
                        statusEl.classList.add('connected');
                        inputSection.style.display = 'block';
                        authBtn.textContent = 'Disconnect Account';
                    }
                });
        }

        function authenticate() {
            window.location.href = '/api/auth-start';
        }

        function findSubreddits() {
            const issue = document.getElementById('issueInput').value.trim();
            if (!issue) {
                showStatus('Please describe your issue', 'error', 'inputStatus');
                return;
            }

            showStatus('Finding subreddits...', 'loading', 'statusMessage');

            fetch('/api/find-subreddits', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ issue: issue })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    displayResults(data.subreddits, data.drafts);
                    showStatus('✅ Posts drafted! Review and approve to post.', 'success', 'statusMessage');
                } else {
                    showStatus(data.error, 'error', 'statusMessage');
                }
            })
            .catch(e => showStatus('Error: ' + e.message, 'error', 'statusMessage'));
        }

        function displayResults(subreddits, drafts) {
            const inputSection = document.getElementById('inputSection');
            const resultsSection = document.getElementById('resultsSection');
            
            inputSection.style.display = 'none';
            resultsSection.style.display = 'block';

            // Display subreddits
            const subList = document.getElementById('subredditsList');
            subList.innerHTML = subreddits.map(sub => `
                <div class="subreddit-item">
                    <h3>${sub.name}</h3>
                    <p>${sub.description}</p>
                    <p><strong>Rules:</strong> ${sub.rules.join(' • ')}</p>
                </div>
            `).join('');

            // Display drafts
            const draftList = document.getElementById('draftsList');
            draftList.innerHTML = drafts.map((draft, i) => `
                <div class="card">
                    <h3 style="color: #ff4500; margin-bottom: 10px;">${draft.subreddit}</h3>
                    <div class="draft-box">${draft.content}</div>
                    <button class="approve-btn" onclick="postNow('${draft.subreddit}', ${i})">
                        ✓ Approve & Post to ${draft.subreddit}
                    </button>
                </div>
            `).join('');
        }

        function postNow(subreddit, draftIndex) {
            showStatus('Posting to ' + subreddit + '...', 'loading', 'statusMessage');

            fetch('/api/post', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subreddit: subreddit })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showStatus(`✅ Posted to ${subreddit}!\n🔗 ${data.post_url}`, 'success', 'statusMessage');
                    // Update button to show posted
                    setTimeout(() => {
                        document.querySelectorAll('.approve-btn')[draftIndex].textContent = '✓ Posted!';
                        document.querySelectorAll('.approve-btn')[draftIndex].disabled = true;
                    }, 100);
                } else {
                    showStatus('❌ Error: ' + data.error, 'error', 'statusMessage');
                }
            })
            .catch(e => showStatus('Error: ' + e.message, 'error', 'statusMessage'));
        }

        function resetForm() {
            document.getElementById('inputSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('issueInput').value = '';
            document.getElementById('statusMessage').innerHTML = '';
        }

        function showStatus(msg, type, elementId) {
            const el = document.getElementById(elementId);
            el.innerHTML = `<div class="status ${type}">${msg}</div>`;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(MOBILE_INTERFACE)

@app.route('/api/auth-status')
def auth_status():
    if 'reddit' in session:
        try:
            reddit_user = session['reddit']
            return jsonify({
                'authenticated': True,
                'username': reddit_user.get('username', 'User')
            })
        except:
            pass
    return jsonify({'authenticated': False})

@app.route('/api/auth-start')
def auth_start():
    global reddit
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        redirect_uri='http://localhost:5000/api/auth-callback'
    )
    auth_url = reddit.auth.url(scopes=['submit', 'read'], state='reddit_agent')
    return redirect(auth_url)

@app.route('/api/auth-callback')
def auth_callback():
    code = request.args.get('code')
    try:
        refresh_token = reddit.auth.authorize(code)
        session['refresh_token'] = refresh_token
        session['reddit'] = {'username': reddit.user.me().name}
        return redirect('/')
    except Exception as e:
        return f"Authentication failed: {str(e)}"

@app.route('/api/find-subreddits', methods=['POST'])
def find_subreddits():
    issue = request.json.get('issue', '')
    
    # Mock subreddit data - in production, use AI to find relevant ones
    subreddits = [
        {
            'name': 'r/techsupport',
            'description': 'For tech troubleshooting and support',
            'rules': ['Describe issue clearly', 'Include what you tried', 'No spam']
        },
        {
            'name': 'r/buildapc',
            'description': 'For PC and hardware questions',
            'rules': ['Use [tags]', 'Include specs', 'Search first']
        },
        {
            'name': 'r/answers',
            'description': 'For straightforward Q&A',
            'rules': ['Direct questions', 'Keep it civil', 'No duplicates']
        }
    ]
    
    drafts = [
        {
            'subreddit': 'r/techsupport',
            'content': f'[HELP] My laptop keeps overheating during gaming\n\nHey everyone, my gaming laptop has been running really hot lately, especially when I\'m playing games. The fans kick into overdrive and it gets uncomfortable. I\'ve cleaned the vents with compressed air and checked Task Manager but the temps still spike when I launch any game. Should I be looking at replacing thermal paste or is there something else I should check?'
        },
        {
            'subreddit': 'r/buildapc',
            'content': f'[Troubleshooting] Laptop getting too hot under load\n\nMy laptop thermal performance has been degrading. When gaming, temps spike immediately. Already tried cleaning dust filters and improving airflow. Before taking it for service, what\'s most likely the problem? Thermal paste degradation or cooling system issue?'
        },
        {
            'subreddit': 'r/answers',
            'content': f'Why does my laptop overheat when gaming and how can I fix it?\n\nMy laptop gets really hot when gaming even though I\'ve cleaned the vents. Is this normal or is something broken? What should I check?'
        }
    ]
    
    return jsonify({
        'success': True,
        'subreddits': subreddits,
        'drafts': drafts
    })

@app.route('/api/post', methods=['POST'])
def post_to_reddit():
    subreddit_name = request.json.get('subreddit', '').replace('r/', '')
    
    if 'refresh_token' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    try:
        # Initialize Reddit with saved token
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            refresh_token=session['refresh_token']
        )
        
        # Get the draft content
        drafts_by_sub = {
            'techsupport': {
                'title': '[HELP] My laptop keeps overheating during gaming',
                'selftext': 'Hey everyone, my gaming laptop has been running really hot lately, especially when I\'m playing games. The fans kick into overdrive and it gets uncomfortable. I\'ve cleaned the vents with compressed air and checked Task Manager but the temps still spike when I launch any game. Should I be looking at replacing thermal paste or is there something else I should check?'
            },
            'buildapc': {
                'title': '[Troubleshooting] Laptop getting too hot under load',
                'selftext': 'My laptop thermal performance has been degrading. When gaming, temps spike immediately. Already tried cleaning dust filters and improving airflow. Before taking it for service, what\'s most likely the problem? Thermal paste degradation or cooling system issue?'
            },
            'answers': {
                'title': 'Why does my laptop overheat when gaming and how can I fix it?',
                'selftext': 'My laptop gets really hot when gaming even though I\'ve cleaned the vents. Is this normal or is something broken? What should I check?'
            }
        }
        
        draft = drafts_by_sub.get(subreddit_name, {})
        
        # Post to subreddit
        submission = reddit.subreddit(subreddit_name).submit(
            title=draft['title'],
            selftext=draft['selftext']
        )
        
        return jsonify({
            'success': True,
            'post_url': f'https://reddit.com{submission.permalink}',
            'post_id': submission.id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        print("⚠️  Missing Reddit credentials!")
        print("Set these environment variables:")
        print("  REDDIT_CLIENT_ID")
        print("  REDDIT_CLIENT_SECRET")
    else:
        app.run(debug=True, host='0.0.0.0', port=5000)
