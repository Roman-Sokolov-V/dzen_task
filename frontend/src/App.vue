<template>
  <div id="app">
    <h1>Коментарі</h1>
    <CommentList :comments="comments" :updateComment="updateCommentById" />
    <CommentForm @commentCreated="handleCommentCreated" />
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
      comments: [],
      ws: null
    }
  },
  mounted() {
    this.connectWebSocket()
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
      } else if (action === 'create' || action === 'update') {
        this.updateCommentById(commentData)
      } else if (action === 'delete') {
        this.removeCommentById(commentData.id)
      }
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
          // Note: We need to include the JWT token if the user is authenticated.
          // For simplicity, we assume the user is authenticated via cookies or localStorage.
          // We'll get the token from localStorage if available.
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
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
</style>