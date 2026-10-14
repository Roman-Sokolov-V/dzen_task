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
      </div>
      <div v-if="showReplyForm === comment.id" class="reply-form">
        <CommentForm :parentId="comment.id" @commentCreated="handleCommentCreated" />
      </div>
      <div v-if="comment.replies && comment.replies.length > 0" class="replies">
        <CommentList :comments="comment.replies" />
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
      showReplyForm: null // The ID of the comment for which the reply form is shown
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