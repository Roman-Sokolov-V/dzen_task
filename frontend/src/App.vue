<template>
  <div id="app">
    <header class="app-header">
      <div class="header-content">
        <span class="app-title">Comments</span>
        <div class="sort-controls">
          <label for="sortSelect">Sort by:</label>
          <select id="sortSelect" v-model="sortOrder" @change="changeSortOrder(sortOrder)">
            <option value="-created_at">Newest first</option>
            <option value="created_at">Oldest first</option>
            <option value="author__username">Author (A–Z)</option>
            <option value="-author__username">Author (Z–A)</option>
            <option value="author__email">Email (A–Z)</option>
            <option value="-author__email">Email (Z–A)</option>
          </select>
        </div>
        <div class="auth-actions" v-if="!token">
          <button class="btn" @click="showLoginModal = true">Log in</button>
          <button class="btn" @click="openRegisterModal">Sign up</button>
        </div>
        <div class="user-info" v-else>
          <span>{{ username }}</span>
          <button class="btn" @click="logout">Log out</button>
        </div>
      </div>
    </header>

    <!-- New comments banner -->
    <div v-if="showNewCommentsBanner" class="new-comments-banner">
      <div class="banner-content">
        New comments ({{ bufferedComments.length }})
        <button class="btn btn-sm" @click="showBufferedComments()">Show new comments</button>
      </div>
    </div>

    <section class="comments-section">
      <div class="comments-toolbar">
        <button
          v-if="token"
          type="button"
          class="add-comment-button"
          @click="showRootCommentForm = !showRootCommentForm"
        >
          {{ showRootCommentForm ? 'Close form' : 'Add new comment' }}
        </button>
        <p v-else class="auth-required-inline">Log in to leave a comment.</p>
      </div>
      <CommentForm
        v-if="token && showRootCommentForm"
        class="root-comment-form"
        @commentCreated="handleCommentCreated"
      />
      <CommentList
        :comments="comments"
        :updateComment="updateCommentById"
        :setLoadedChildren="setLoadedChildren"
        :hasLoadedChildren="hasLoadedChildren"
        :getCommentChildren="getCommentChildren"
        :token="token"
        :newReplyCounts="newReplyCounts"
        :clearReplyNotifications="clearReplyNotifications"
        :lastCreatedReply="lastCreatedReply"
        @commentCreated="handleCommentCreated"
      />
    </section>
    <!-- Load more button -->
    <div v-if="hasMore && !loadingMore" class="load-more-container">
      <button class="btn btn-primary" @click="loadNextPage">Load more</button>
    </div>
    <div v-else-if="loadingMore" class="load-more-container">
      <button class="btn btn-primary" disabled>Loading...</button>
    </div>
    <div v-else-if="!hasMore" class="load-more-container">
      <button class="btn btn-primary" disabled>No more comments</button>
    </div>
    <!-- Login Modal -->
    <div v-if="showLoginModal" class="modal-overlay" @click.self="showLoginModal = false">
      <div class="modal">
        <h2>Log in</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label>Username:</label>
            <input type="text" v-model="login.username" required />
          </div>
          <div class="form-group">
            <label>Password:</label>
            <input type="password" v-model="login.password" required />
          </div>
          <div class="form-group" v-if="loginError">
            <p class="error">{{ loginError }}</p>
          </div>
          <button type="submit" :disabled="loginLoading">Log in</button>
        </form>
      </div>
    </div>

    <!-- Register Modal -->
    <div v-if="showRegisterModal" class="modal-overlay" @click.self="showRegisterModal = false">
      <div class="modal">
        <h2>Sign up</h2>
        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label>Username:</label>
            <input type="text" v-model="register.username" required />
          </div>
          <div class="form-group">
            <label>Email:</label>
            <input type="email" v-model="register.email" required />
          </div>
          <div class="form-group">
            <label>Password:</label>
            <input type="password" v-model="register.password" required />
          </div>
          <div class="form-group">
            <label>Confirm password:</label>
            <input type="password" v-model="register.password2" required />
          </div>
          <div class="form-group captcha-group">
            <label for="registration-captcha">{{ register.captchaQuestion || 'Loading CAPTCHA...' }}</label>
            <input
              id="registration-captcha"
              type="text"
              inputmode="numeric"
              autocomplete="off"
              v-model="register.captchaAnswer"
              :disabled="captchaLoading || !register.captchaKey"
              required
            />
            <button type="button" class="captcha-refresh" @click="loadCaptcha" :disabled="captchaLoading">
              {{ captchaLoading ? 'Loading...' : 'Get a new question' }}
            </button>
          </div>
          <div class="form-group" v-if="registerError">
            <p class="error">{{ registerError }}</p>
          </div>
          <button type="submit" :disabled="registerLoading || captchaLoading || !register.captchaKey">
            {{ registerLoading ? 'Creating account...' : 'Sign up' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import CommentList from './components/CommentList.vue'
import CommentForm from './components/CommentForm.vue'

export default {
  name: 'App',
  components: {
    CommentList,
    CommentForm
  },
  data() {
    return {
      comments: [], // Array of root comments (received from WebSocket), already sorted by sortOrder
      ws: null,
      sortOrder: '-created_at', // Default sorting: newest first
      loadedChildrenMap: new Map(), // Map of comment ID to its loaded children tree
      token: localStorage.getItem('access_token') || '', // JWT токен автентифікації
      usernameFromStorage: '',
      // Pagination
      pageOffset: 0,
      pageLimit: 5, // Default page size, should match backend PAGE_SIZE
      loadingMore: false,
      hasMore: true,
      // Buffered new comments (arrived via WebSocket since last fetch)
      bufferedComments: [],
      bufferedReplies: {},
      lastCreatedReply: null,
      showRootCommentForm: false,
      showNewCommentsBanner: false,
      login: {
        username: '',
        password: ''
      },
      register: {
        username: '',
        email: '',
        password: '',
        password2: '',
        captchaKey: '',
        captchaQuestion: '',
        captchaAnswer: ''
      },
      captchaLoading: false,
      showLoginModal: false,
      showRegisterModal: false,
      loginLoading: false,
      loginError: '',
      registerLoading: false,
      registerError: ''
    }
  },
  computed: {
    newReplyCounts() {
      return Object.fromEntries(
        Object.entries(this.bufferedReplies).map(([rootId, replies]) => [rootId, replies.length])
      )
    },
    username() {
      if (this.usernameFromStorage) {
        return this.usernameFromStorage
      }
      const token = this.token
      if (!token) {
        return ''
      }
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        return payload.username || payload.user_id || 'User'
      } catch (e) {
        return ''
      }
    }
  },
  mounted() {
    this.connectWebSocket()
    const storedUsername = localStorage.getItem('username')
    if (storedUsername) {
      this.usernameFromStorage = storedUsername
    }
  },
  beforeUnmount() {
    this.disconnectWebSocket()
  },
  methods: {
    openRegisterModal() {
      this.showRegisterModal = true
      this.registerError = ''
      this.loadCaptcha()
    },
    loadCaptcha() {
      this.captchaLoading = true
      this.register.captchaKey = ''
      this.register.captchaQuestion = ''
      this.register.captchaAnswer = ''

      fetch('/api/captcha/')
        .then(response => {
          if (!response.ok) {
            throw new Error('Unable to load CAPTCHA')
          }
          return response.json()
        })
        .then(data => {
          this.register.captchaKey = data.captcha_key
          this.register.captchaQuestion = data.question
        })
        .catch(error => {
          console.error('CAPTCHA loading error:', error)
          this.registerError = 'Could not load the CAPTCHA. Please try again.'
        })
        .finally(() => {
          this.captchaLoading = false
        })
    },
    connectWebSocket() {
      // Connect to the websocket endpoint (relative URL, proxied by nginx)
      const ws = new WebSocket(`/ws/comments/`)
      this.ws = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        // Fetch first page after connection is open
        this.fetchPage(0)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.handleWebSocketMessage(data)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    },
    disconnectWebSocket() {
      if (this.ws) {
        this.ws.close()
      }
    },
    handleWebSocketMessage(data) {
      const { action, data: commentData } = data
      if (action === 'initial_comments') {
        // Determine if this is first page or subsequent page based on offset sent
        // We don't have offset in message, so we rely on pageOffset in data.
        // If pageOffset is 0, replace; else append.
        if (this.pageOffset === 0) {
          this.comments = commentData
          // When replacing, clear loaded children map as we have a new set
          this.loadedChildrenMap.clear()
        } else {
          // Append new comments to existing list
          this.comments = [...this.comments, ...commentData]
          // If we got fewer comments than limit, assume no more pages
          if (commentData.length < this.pageLimit) {
            this.hasMore = false
          }
        }
        this.loadingMore = false
      } else if (action === 'create') {
        if (commentData.parent == null) {
          if (!this.bufferedComments.some(comment => comment.id === commentData.id)) {
            this.bufferedComments.push(commentData)
          }
          this.showNewCommentsBanner = true
        } else if (commentData.root_id != null) {
          const rootId = String(commentData.root_id)
          const replies = this.bufferedReplies[rootId] || []
          if (!replies.some(comment => comment.id === commentData.id)) {
            this.bufferedReplies[rootId] = [...replies, commentData]
          }
        } else {
          console.error('Reply WebSocket message is missing root_id:', commentData)
        }
      } else if (action === 'update') {
        this.updateCommentById(commentData)
        // Clear loaded children map as comment data may have changed
        this.loadedChildrenMap.clear()
      } else if (action === 'delete') {
        this.removeCommentById(commentData.id)
        // Clear loaded children map as comment data may have changed
        this.loadedChildrenMap.clear()
      }
    },
    changeSortOrder(newOrder) {
      // v-model already updated this.sortOrder, but we ensure it's set
      this.sortOrder = newOrder
      // Reset pagination
      this.pageOffset = 0
      this.hasMore = true
      // Clear loaded children map as we have a new set
      this.loadedChildrenMap.clear()
      // Clear buffered comments and hide banner
      this.bufferedComments = []
      this.showNewCommentsBanner = false
      // Send WebSocket message to change ordering on server and fetch first page
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          action: 'change_ordering',
          ordering: newOrder
        }))
      }
    },
    fetchPage(offset) {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          action: 'fetch_paginated_comments',
          offset: offset,
          limit: this.pageLimit
        }))
      }
    },
    loadNextPage() {
      if (this.loadingMore || !this.hasMore) return
      this.loadingMore = true
      const nextOffset = this.pageOffset + this.pageLimit
      this.fetchPage(nextOffset)
      // Note: actual offset update will happen when we receive the response
      // We'll update pageOffset in handleWebSocketMessage when we append.
      // For simplicity, we update offset after sending request optimistically.
      this.pageOffset = nextOffset
    },
    setLoadedChildren(commentId, children) {
      // Store the loaded children tree for a comment
      this.loadedChildrenMap.set(commentId, children)
    },
    hasLoadedChildren(commentId) {
      return this.loadedChildrenMap.has(commentId)
    },
    getCommentChildren(commentId) {
      return this.loadedChildrenMap.get(commentId) || []
    },
    updateCommentById(comment) {
      // Remove from comments array if present and re-insert to maintain sort order
      const index = this.comments.findIndex(c => c.id === comment.id)
      if (index !== -1) {
        this.comments.splice(index, 1)
      }
      this.insertCommentIntoSortedArray(comment)

      // Update in bufferedComments array (if present) - replace in place
      const buffIndex = this.bufferedComments.findIndex(c => c.id === comment.id)
      if (buffIndex !== -1) {
        this.bufferedComments.splice(buffIndex, 1, comment)
      }
    },
    removeCommentById(id) {
      const index = this.comments.findIndex(c => c.id === id)
      if (index !== -1) {
        this.comments.splice(index, 1)
      }
      const buffIndex = this.bufferedComments.findIndex(c => c.id === id)
      if (buffIndex !== -1) {
        this.bufferedComments.splice(buffIndex, 1)
      }
      // Remove from loaded children map
      this.loadedChildrenMap.delete(id)
    },
    // Helper: compare two comments based on the current sortOrder
    compareComments(a, b) {
      const order = this.sortOrder
      // Determine if order is descending
      const descending = order.startsWith('-')
      const field = descending ? order.substring(1) : order

      let valA, valB
      if (field === 'created_at') {
        valA = new Date(a.created_at)
        valB = new Date(b.created_at)
      } else if (field === 'author__username') {
        valA = a.author
        valB = b.author
      } else if (field === 'author__email') {
        valA = a.email
        valB = b.email
      } else {
        // Fallback to created_at
        valA = new Date(a.created_at)
        valB = new Date(b.created_at)
      }

      if (descending) {
        // For descending, we want higher values first
        if (valA < valB) return 1
        if (valA > valB) return -1
        return 0
      } else {
        // For ascending
        if (valA < valB) return -1
        if (valA > valB) return 1
        return 0
      }
    },

    // Insert a comment into the sorted comments array
    insertCommentIntoSortedArray(comment) {
      // If the array is empty, just push
      if (this.comments.length === 0) {
        this.comments.push(comment)
        return
      }

      // Binary search to find the insertion index
      let low = 0
      let high = this.comments.length
      while (low < high) {
        const mid = Math.floor((low + high) / 2)
        const cmp = this.compareComments(comment, this.comments[mid])
        if (cmp < 0) {
          high = mid
        } else {
          low = mid + 1
        }
      }
      // Insert at index low
      this.comments.splice(low, 0, comment)
    },

    showBufferedComments() {
      this.bufferedComments.forEach(comment => this.insertCommentIntoSortedArray(comment));
      this.bufferedComments = [];
      this.showNewCommentsBanner = false;
    },

    clearReplyNotifications(rootId, loadedReplies) {
      const loadedIds = new Set()
      const collectIds = replies => {
        replies.forEach(reply => {
          loadedIds.add(reply.id)
          collectIds(reply.children || [])
        })
      }
      collectIds(loadedReplies)

      const key = String(rootId)
      const remainingReplies = (this.bufferedReplies[key] || [])
        .filter(reply => !loadedIds.has(reply.id))
      if (remainingReplies.length) {
        this.bufferedReplies[key] = remainingReplies
      } else {
        delete this.bufferedReplies[key]
      }
    },

    handleCommentCreated(formData) {
      if (!this.token) {
        console.error('No token available')
        // Optionally, show a message to the user or redirect to login
        return
      }
      // Send the new comment to the backend via REST API using multipart/form-data
      fetch('/api/comments/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`
          // Let the browser set the Content-Type for multipart/form-data
        },
        body: formData
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok')
        }
        return response.json()
      })
      .then(data => {
        console.log('Comment created:', data)
        const parentId = formData.get('parent')
        if (parentId !== null) {
          this.lastCreatedReply = { parentId: Number(parentId), commentId: data.id }
        } else {
          this.showRootCommentForm = false
        }
        // The websocket will broadcast the creation, so we don't need to update the list here.
      })
      .catch(error => {
        console.error('Error creating comment:', error)
      })
    },
    handleLogin() {
      this.loginLoading = true
      this.loginError = ''
      fetch('/api/user/token/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: this.login.username,
          password: this.login.password
        })
      })
      .then(response => {
        if (!response.ok) {
          return response.json().then(err => { throw err })
        }
        return response.json()
      })
      .then(data => {
        const { access, refresh } = data
        this.token = access
        localStorage.setItem('access_token', access)
        localStorage.setItem('refresh_token', refresh)
        // Fetch user profile to get username
        // First decode token to get user_id
        let userId
        try {
          const payload = JSON.parse(atob(access.split('.')[1]))
          userId = payload.user_id
        } catch (e) {
          console.error('Failed to decode token:', e)
          userId = null
        }
        if (userId) {
          fetch(`/api/user/${userId}/`, {
            headers: {
              'Authorization': `Bearer ${access}`
            }
          })
          .then(resp => {
            if (!resp.ok) {
              throw new Error('Failed to fetch user profile')
            }
            return resp.json()
          })
          .then(userData => {
            const username = userData.username || ''
            this.usernameFromStorage = username
            localStorage.setItem('username', username)
          })
          .catch(err => {
            console.error('Failed to fetch user profile:', err)
            // fallback: maybe token contains username?
            try {
              const payload = JSON.parse(atob(access.split('.')[1]))
              const usernameFromToken = payload.username || ''
              if (usernameFromToken) {
                this.usernameFromStorage = usernameFromToken
                localStorage.setItem('username', usernameFromToken)
              }
            } catch (e) {
              /* ignore */
            }
          })
        }
        this.showLoginModal = false
        // Clear login form
        this.login.username = ''
        this.login.password = ''
      })
      .catch(err => {
        console.error('Login error:', err)
        this.loginError = err.detail || 'Login failed'
      })
      .finally(() => {
        this.loginLoading = false
      })
    },
    handleRegister() {
      if (this.register.password !== this.register.password2) {
        this.registerError = 'Passwords do not match'
        return
      }
      this.registerLoading = true
      this.registerError = ''
      fetch('/api/user/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: this.register.username,
          email: this.register.email,
          password: this.register.password,
          captcha_key: this.register.captchaKey,
          captcha_value: this.register.captchaAnswer
        })
      })
      .then(response => {
        if (!response.ok) {
          return response.json().then(err => { throw err })
        }
        return response.json()
      })
      .then(data => {
        console.log('Registration successful:', data)
        // Store username from registration response
        const username = data.username || ''
        this.usernameFromStorage = username
        localStorage.setItem('username', username)
        this.showRegisterModal = false
        // Clear register form
        this.register.username = ''
        this.register.email = ''
        this.register.password = ''
        this.register.password2 = ''
        this.register.captchaKey = ''
        this.register.captchaQuestion = ''
        this.register.captchaAnswer = ''
        // Show success message and prompt to login
        alert('Registration successful! You can now log in.')
        this.showLoginModal = true
        this.login.username = username // pre-fill username
      })
      .catch(err => {
        console.error('Registration error:', err)
        this.registerError = this.getRegistrationErrorMessage(err)
        this.loadCaptcha()
      })
      .finally(() => {
        this.registerLoading = false
      })
    },
    getRegistrationErrorMessage(error) {
      if (error.detail) return error.detail
      const messages = Object.entries(error)
        .flatMap(([, value]) => Array.isArray(value) ? value : [value])
        .filter(value => typeof value === 'string')
      return messages.join(' ') || 'Registration failed. Please check your details and try again.'
    },
    logout() {
      this.token = ''
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('username')
      // Optionally clear comments? Not necessary.
      this.usernameFromStorage = ''
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}
.header-content {
  display: flex;
  align-items: center;
  gap: 2rem;
  width: 100%;
}
.app-title {
  font-size: 1.5rem;
  font-weight: bold;
  color: #2c3e50;
}
.auth-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: auto;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: auto;
}
.btn {
  padding: 0.5rem 1rem;
  font-size: 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.btn-primary {
  background-color: #007bff;
  color: white;
}
.btn-primary:hover {
  background-color: #0056b3;
}
.btn-secondary {
  background-color: #6c757d;
  color: white;
}
.btn-secondary:hover {
  background-color: #545b62;
}
.btn-danger {
  background-color: #dc3545;
  color: white;
}
.btn-danger:hover {
  background-color: #c82333;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.modal h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #2c3e50;
  text-align: center;
}
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}
.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
}
.form-group input:focus {
  outline: none;
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}
.error {
  color: #dc3545;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}
button[type="submit"] {
  width: 100%;
  padding: 0.75rem;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}
button[type="submit"]:hover {
  background-color: #218838;
}
button[type="submit"]:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
.load-more-container {
  margin: 2rem 0;
  text-align: center;
}
.comments-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 12px;
}
.add-comment-button {
  padding: 0.6rem 1rem;
  color: white;
  background-color: #42b983;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}
.add-comment-button:hover {
  background-color: #369870;
}
.auth-required-inline {
  margin: 0;
  color: #666;
}
.new-comments-banner {
  background-color: #fffae6;
  border: 1px solid #ffd28f;
  color: #8a6d3b;
  padding: 0.75rem 1.5rem;
  margin-bottom: 1rem;
  text-align: center;
}
.banner-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.banner-content button {
  font-size: 0.875rem;
  padding: 0.25rem 0.5rem;
  background-color: #ffd28f;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}
.banner-content button:hover {
  background-color: #ffc76f;
}
.auth-required {
  padding: 2rem;
  text-align: center;
  color: #666;
}
</style>