<template>
  <div id="app">
    <header class="app-header">
      <div class="header-content">
        <span class="app-title">Коментарі</span>
        <div class="sort-controls">
          <label for="sortSelect">Сортування:</label>
          <select id="sortSelect" v-model="sortOrder" @change="changeSortOrder(sortOrder)">
            <option value="-created_at">Новіші спочатку</option>
            <option value="created_at">Старіші спочатку</option>
            <option value="author__username">Автор (А-Я)</option>
            <option value="-author__username">Автор (Я-А)</option>
            <option value="author__email">Email (А-Я)</option>
            <option value="-author__email">Email (Я-А)</option>
          </select>
        </div>
        <div class="auth-actions" v-if="!token">
          <button class="btn" @click="showLoginModal = true">Увійти</button>
          <button class="btn" @click="showRegisterModal = true">Зареєструватися</button>
        </div>
        <div class="user-info" v-else>
          <span>{{ username }}</span>
          <button class="btn" @click="logout">Вийти</button>
        </div>
      </div>
    </header>

    <CommentList :comments="sortedRootComments" :updateComment="updateCommentById" :setLoadedChildren="setLoadedChildren" :hasLoadedChildren="hasLoadedChildren" :getCommentChildren="getCommentChildren" />
    <CommentForm @commentCreated="handleCommentCreated" />

    <!-- Login Modal -->
    <div v-if="showLoginModal" class="modal-overlay" @click.self="showLoginModal = false">
      <div class="modal">
        <h2>Увійти</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label>Ім'я користувача:</label>
            <input type="text" v-model="login.username" required />
          </div>
          <div class="form-group">
            <label>Пароль:</label>
            <input type="password" v-model="login.password" required />
          </div>
          <div class="form-group" v-if="loginError">
            <p class="error">{{ loginError }}</p>
          </div>
          <button type="submit" :disabled="loginLoading">Увійти</button>
        </form>
      </div>
    </div>

    <!-- Register Modal -->
    <div v-if="showRegisterModal" class="modal-overlay" @click.self="showRegisterModal = false">
      <div class="modal">
        <h2>Реєстрація</h2>
        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label>Ім'я користувача:</label>
            <input type="text" v-model="register.username" required />
          </div>
          <div class="form-group">
            <label>Електронна пошта:</label>
            <input type="email" v-model="register.email" required />
          </div>
          <div class="form-group">
            <label>Пароль:</label>
            <input type="password" v-model="register.password" required />
          </div>
          <div class="form-group">
            <label>Повторіть пароль:</label>
            <input type="password" v-model="register.password2" required />
          </div>
          <div class="form-group" v-if="registerError">
            <p class="error">{{ registerError }}</p>
          </div>
          <button type="submit" :disabled="registerLoading">Зареєструватися</button>
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
      comments: [], // Array of root comments (received from WebSocket)
      ws: null,
      sortOrder: '-created_at', // Default sorting: newest first
      loadedChildrenMap: new Map(), // Map of comment ID to its loaded children tree
      token: localStorage.getItem('access_token') || '',
      usernameFromStorage: '',
      login: {
        username: '',
        password: ''
      },
      register: {
        username: '',
        email: '',
        password: '',
        password2: ''
      },
      showLoginModal: false,
      showRegisterModal: false,
      loginLoading: false,
      loginError: '',
      registerLoading: false,
      registerError: ''
    }
  },
  computed: {
    username() {
      if (this.usernameFromStorage) {
        return this.usernameFromStorage
      }
      if (!this.token) {
        return ''
      }
      try {
        const payload = JSON.parse(atob(this.token.split('.')[1]))
        return payload.username || payload.user_id || 'Користувач'
      } catch (e) {
        return ''
      }
    },
    sortedRootComments() {
      // Sort comments based on current sortOrder
      // We create a new array to avoid mutating the original comments array
      const sorted = [...this.comments]
      if (this.sortOrder === 'created_at') {
        sorted.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      } else if (this.sortOrder === '-created_at') {
        sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      } else if (this.sortOrder === 'author__username') {
        sorted.sort((a, b) => a.author.localeCompare(b.author))
      } else if (this.sortOrder === '-author__username') {
        sorted.sort((a, b) => b.author.localeCompare(a.author))
      } else if (this.sortOrder === 'author__email') {
        sorted.sort((a, b) => a.email.localeCompare(b.email))
      } else if (this.sortOrder === '-author__email') {
        sorted.sort((a, b) => b.email.localeCompare(a.email))
      }
      // Default to -created_at if sortOrder is not recognized
      else {
        sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      }
      return sorted
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
    connectWebSocket() {
      // Connect to the websocket endpoint (relative URL, proxied by nginx)
      const ws = new WebSocket(`/ws/comments/`)
      this.ws = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
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
        this.comments = commentData
        // Clear loaded children map as we have a completely new set of comments
        this.loadedChildrenMap.clear()
      } else if (action === 'create' || action === 'update') {
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
      if (this.sortOrder !== newOrder) {
        this.sortOrder = newOrder
        // Send WebSocket message to change ordering on server
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({
            action: 'change_ordering',
            ordering: newOrder
          }))
        }
      }
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
      const index = this.comments.findIndex(c => c.id === comment.id)
      if (index !== -1) {
        this.comments.splice(index, 1, comment)
      } else {
        // If not found, we can add it (should not happen for updates, but just in case)
        this.comments.push(comment)
      }
    },
    removeCommentById(id) {
      const index = this.comments.findIndex(c => c.id === id)
      if (index !== -1) {
        this.comments.splice(index, 1)
      }
    },
    handleCommentCreated(comment) {
      // Send the new comment to the backend via REST API
      fetch('/api/comments/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify(comment)
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok')
        }
        return response.json()
      })
      .then(data => {
        console.log('Comment created:', data)
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
        this.loginError = err.detail || 'Помилка входу'
      })
      .finally(() => {
        this.loginLoading = false
      })
    },
    handleRegister() {
      if (this.register.password !== this.register.password2) {
        this.registerError = 'Паролі не співпадають'
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
          password: this.register.password
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
        // Show success message and prompt to login
        alert('Реєстрація успішна! Тепер ви можете увійти.')
        this.showLoginModal = true
        this.login.username = username // pre-fill username
      })
      .catch(err => {
        console.error('Registration error:', err)
        this.registerError = err.detail || 'Помилка реєстрації'
      })
      .finally(() => {
        this.registerLoading = false
      })
    },
    logout() {
      this.token = ''
      this.usernameFromStorage = ''
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('username')
      // Optionally clear comments? Not necessary.
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
}
.app-title {
  font-size: 1.5rem;
  font-weight: bold;
  color: #2c3e50;
}
.auth-actions {
  display: flex;
  gap: 0.5rem;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
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
</style>