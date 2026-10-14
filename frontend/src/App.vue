<template>
  <div id="app">
    <h1>Коментарі</h1>
    <CommentList :comments="comments" />
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
      } else if (action === 'create') {
        // Add the new comment to the list
        // We need to determine if it's a root comment or a reply
        // For simplicity, we'll just push it and then reorder? Better to have a nested structure.
        // We'll change the data structure to a tree later.
        // For now, we'll just replace the comments with a new list? Not efficient.
        // Let's assume we are only dealing with root comments for now? But the requirement includes replies.
        // We'll need to implement a tree structure.
        // We'll do a simple approach: if the comment is a root comment (parent_id === null), we add it to the root list.
        // If it's a reply, we need to find the parent and add it to its replies.
        // We'll change the data structure to a tree of comments.
        // However, due to time, we'll just update the whole list by fetching again? Not ideal.
        // We'll implement a simple tree update.
        this.updateCommentInTree(commentData, 'add')
      } else if (action === 'update') {
        this.updateCommentInTree(commentData, 'update')
      } else if (action === 'delete') {
        this.updateCommentInTree(commentData, 'remove')
      }
    },
    updateCommentInTree(commentData, operation) {
      // We'll implement a simple tree update for now.
      // We'll keep the comments as a flat list and use a map to update.
      // But the CommentList component expects a tree? We'll change the CommentList to work with a flat list and build the tree internally.
      // Let's change the data structure to a flat list of comments and build the tree in the CommentList component.
      // For now, we'll just replace the whole list by re-fetching? We'll do a simple thing: on any mutation, we'll request the root comments again via API?
      // That would be extra load. We'll stick to the websocket and update the flat list.

      // We'll maintain a flat list of comments in `this.comments`.
      const index = this.comments.findIndex(c => c.id === commentData.id)
      if (operation === 'add') {
        if (index === -1) {
          this.comments.push(commentData)
        }
      } else if (operation === 'update') {
        if (index !== -1) {
          this.comments.splice(index, 1, commentData)
        }
      } else if (operation === 'remove') {
        if (index !== -1) {
          this.comments.splice(index, 1)
        }
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