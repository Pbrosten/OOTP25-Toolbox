<template>
  <header class="main-header">
    <h1>OOTP25 GM Toolbox</h1>
    <nav>
      <router-link to="/">Home</router-link>
      <router-link to="/search">Find a Player</router-link>
    </nav>
  </header>
</template>

<script>
export default {
  name: 'Header'
}
</script>

<style scoped>
.main-header {
  text-align: center;
  padding: 2rem 0 1rem 0;
  background: var(--color-primary);
  color: var(--color-text);
  border-radius: 0 0 16px 16px;
  box-shadow: 0 2px 8px rgba(30,41,59,0.08);
}

.main-header h1 {
  margin: 0;
  font-size: 2.5rem;
  letter-spacing: 1px;
}

.main-header p {
  margin: 0.5rem 0 0 0;
  font-size: 1.2rem;
  color: #cbd5e1;
}
nav a {
  margin-right: 1rem;
  color: white;
  text-decoration: none;
}
</style>