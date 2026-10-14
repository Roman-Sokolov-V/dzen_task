<template>
  <div>
    <div v-for="comment in comments" :key="comment.id" class="comment">
      <div class="comment-header">
        <strong>{{ comment.author }}</strong>
        <span>{{ new Date(comment.created_at).toLocaleString() }}</span>
      </div>
      <div class="comment-content" v-html="comment.content"></div>
      <div class="comment-actions">
        <button @click="toggleReplyForm(comment.id)">Reply</button>
        <button @click="toggleExpand(comment)" class="expand-btn">{{ expanded[comment.id] ? 'Згорнути' : 'Розгорнути' }}</button>
      </div>
      <div v-if="showReplyForm === comment.id" class="reply-form">
        <CommentForm :parentId="comment.id" @commentCreated="handleCommentCreated" />
      </div>
      <div v-if="expanded[comment.id]" class="replies">
        <CommentList v-if="hasLoadedChildren(comment.id)" :comments="getCommentChildren(comment.id)" :updateComment="updateComment" :setLoadedChildren="setLoadedChildren" :getCommentChildren="getCommentChildren" :hasLoadedChildren="hasLoadedChildren" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CommentList',
  props: {
    comments: {
      type: Array,
      required: true
      // Array of comment objects (flat, without children field)
      // Each comment has fields: id, author, content, created_at, image, file, etc.
    },
    updateComment: {
      type: Function,
      required: true
    },
    setLoadedChildren: {
      type: Function,
      required: true
    },
    hasLoadedChildren: {
      type: Function,
      required: true
    },
    getCommentChildren: {
      type: Function,
      required: true
    }
  },
  data() {
    return {
      showReplyForm: null, // The ID of the comment for which the reply form is shown
      expanded: {} // Map of comment ID to boolean indicating if replies are shown
    }
  },
  watch: {
    comments(newVal, oldVal) {
      // Reset expanded state when comments list changes significantly
      // In practice, we might want to preserve expanded state for existing comments
      // For simplicity, we reset it when the comments array changes
      this.expanded = {}
    }
  },
  methods: {
    toggleReplyForm(commentId) {
      if (this.showReplyForm === commentId) {
        this.showReplyForm = null
      } else {
        this.showReplyForm = commentId
      }
    },
    toggleExpand(comment) {
      const commentId = comment?.id
      if (!commentId) {
        console.error('commentId is undefined or null')
        return
      }
      const vm = this
      if (vm.expanded[commentId]) {
        // Collapse
        vm.expanded[commentId] = false
      } else {
        // Expand: fetch the comment tree if children are not yet loaded
        if (!vm.hasLoadedChildren(commentId)) {
          fetch(`/api/comments/${commentId}/tree/`)
            .then(response => {
              if (!response.ok) {
                throw new Error('Network response was not ok')
              }
              return response.json()
            })
            .then(apiTreeData => {
              // Extract direct replies from the API response
              const apiReplies = apiTreeData.replies || []
              // Convert the replies array from API format to our internal format
              const childrenData = apiReplies.map(reply => vm.convertApiTreeToInternalFormat(reply))
              // Store the loaded children in the parent App.vue
              vm.setLoadedChildren(commentId, childrenData)
              // Mark as expanded
              vm.expanded[commentId] = true
            })
            .catch(error => {
              console.error('Error fetching comment tree:', error)
            })
        } else {
          // Children are already loaded, just toggle expanded state
          vm.expanded[commentId] = true
        }
      }
    },
    // Convert API tree format (using 'replies') to our internal format (using 'children')
    convertApiTreeToInternalFormat(apiComment) {
      if (!apiComment) return null
      // Create a copy of the comment without the 'replies' field
      const { replies, ...commentWithoutReplies } = apiComment
      // Initialize children array
      const commentWithChildren = { ...commentWithoutReplies, children: [] }
      // Recursively convert replies to children
      if (Array.isArray(replies)) {
        commentWithChildren.children = replies.map(reply => this.convertApiTreeToInternalFormat(reply))
      }
      return commentWithChildren
    },
    getChildrenForComment(commentId) {
      // Return the loaded children for a comment, or empty array if not loaded
      return this.getCommentChildren(commentId) || []
    },
    handleCommentCreated(comment) {
      // Emit an event to the parent to update the comments list
      this.$emit('commentCreated', comment)
    }
  }
}
</script>

<style>
.comment {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}
.comment-header {
  display: flex;
  justify-content: space-between;
  font-size: 0.9em;
  color: #666;
}
.comment-content {
  margin: 16px 0;
  line-height: 1.5;
}
.comment-actions {
  text-align: right;
}
button {
  background-color: #42b983;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
button:hover {
  background-color: #369870;
}
.expand-btn {
  margin-left: 8px;
}
.reply-form {
  margin-top: 16px;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 4px;
}
.replies {
  margin-left: 32px;
  border-left: 2px solid #eee;
  padding-left: 16px;
}
</style>