<template>
  <div>
    <h3>{{ parentId ? 'Відповісти на коментар' : 'Додати коментар' }}</h3>
    <form @submit.prevent="onSubmit">
      <div>
        <label for="content">Вміст:</label>
        <textarea id="content" v-model="content" required></textarea>
      </div>
      <div>
        <button type="submit">Надіслати</button>
      </div>
    </form>
  </div>
</template>

<script>
export default {
  name: 'CommentForm',
  props: {
    parentId: {
      type: [Number, String],
      default: null
    }
  },
  data() {
    return {
      content: ''
    }
  },
  methods: {
    onSubmit() {
      if (!this.content.trim()) {
        return
      }
      const commentData = {
        content: this.content,
        parent_id: this.parentId
      }
      this.$emit('commentCreated', commentData)
      this.content = ''
    }
  }
}
</script>

<style>
label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}
textarea {
  width: 100%;
  height: 100px;
  padding: 8px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
}
button {
  margin-top: 16px;
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
</style>