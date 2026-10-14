<template>
  <div>
    <h3>{{ parentId ? 'Відповісти на коментар' : 'Додати коментар' }}</h3>
    <form @submit.prevent="onSubmit">
      <div>
        <label for="content">Вміст:</label>
        <textarea id="content" v-model="content" required></textarea>
      </div>
      <div>
        <label for="image">Зображення (необов'язково):</label>
        <input id="image" type="file" accept="image/*" @change="onImageChange" />
      </div>
      <div>
        <label for="file">Текстовий файл (необов'язково):</label>
        <input id="file" type="file" accept=".txt" @change="onFileChange" />
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
      content: '',
      imageFile: null,
      fileFile: null
    }
  },
  methods: {
    onImageChange(event) {
      this.imageFile = event.target.files[0] || null
    },
    onFileChange(event) {
      this.fileFile = event.target.files[0] || null
    },
    onSubmit() {
      if (!this.content.trim()) {
        return
      }

      const formData = new FormData()
      formData.append('content', this.content)
      if (this.parentId !== null) {
        formData.append('parent', this.parentId)
      }
      if (this.imageFile) {
        formData.append('image', this.imageFile)
      }
      if (this.fileFile) {
        formData.append('file', this.fileFile)
      }

      this.$emit('commentCreated', formData)
      this.content = ''
      this.imageFile = null
      this.fileFile = null
      // Reset file inputs
      const imageInput = document.getElementById('image')
      const fileInput = document.getElementById('file')
      if (imageInput) imageInput.value = ''
      if (fileInput) fileInput.value = ''
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
textarea,
input[type="file"] {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
}
textarea {
  height: 100px;
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