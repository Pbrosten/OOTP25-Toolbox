<template>
  <header class="text-center px-4 py-8 bg-teal-800 text-white rounded-b-2xl shadow-md">
    <h1 class="m-0 text-4xl tracking-wide">OOTP25 GM Toolbox</h1>
    <nav class="mt-4">
      <router-link to="/" class="mr-4 hover:underline">Home</router-link>
      <router-link to="/search" class="hover:underline">Find a Player</router-link>
    </nav>
  </header>
</template>

<script>
export default {
  name: 'Header',
}
</script>
