<template>
  <div>
    <div v-for="comment in rootComments" :key="comment.id" class="comment">
      <div class="comment-header">
        <strong>{{ comment.author }}</strong>
        <span>{{ new Date(comment.created_at).toLocaleString() }}</span>
      </div>
      <div class="comment-content" v-html="comment.content"></div>
      <div class="comment-actions">
        <button @click="toggleReplyForm(comment.id)">Reply</button>
        <button @click="toggleExpand(comment)" class="expand-btn">{{ expanded[comment.id] ? 'Collapse' : 'Expand' }}</button>
      </div>
      <div v-if="showReplyForm === comment.id" class="reply-form">
        <CommentForm :parentId="comment.id" @commentCreated="handleCommentCreated" />
      </div>
      <div v-if="expanded[comment.id] && comment.replies && comment.replies.length > 0" class="replies">
        <CommentList :comments="comment.replies" :updateComment="updateComment" />
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
    },
    updateComment: {
      type: Function,
      required: true
    }
  },
  computed: {
    rootComments() {
      // Filter out comments that have a parent (i.e., are replies)
      return this.comments.filter(comment => !comment.parent_id)
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
      console.log('toggleExpand called with commentId:', commentId)
      if (!commentId) {
        console.error('commentId is undefined or null')
        return
      }
      const vm = this
      if (vm.expanded[commentId]) {
        // Collapse
        vm.expanded[commentId] = false
      } else {
        // Expand: fetch the comment tree
        fetch(`/api/comments/${commentId}/tree/`)
          .then(response => {
            if (!response.ok) {
              throw new Error('Network response was not ok')
            }
            return response.json()
          })
          .then(treeData => {
            // Update the comment and all its descendants in the flat list
            vm.updateCommentTree(treeData)
            // Mark as expanded
            vm.expanded[commentId] = true
          })
          .catch(error => {
            console.error('Error fetching comment tree:', error)
          })
      }
    },
    updateCommentTree(tree) {
      // Update the current node
      this.updateComment(tree)
      // Recursively update replies
      if (tree.replies && Array.isArray(tree.replies)) {
        tree.replies.forEach(reply => {
          this.updateCommentTree(reply)
        })
      }
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