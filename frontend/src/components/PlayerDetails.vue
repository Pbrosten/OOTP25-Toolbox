<script setup lang="ts">

defineProps<{ playerId: number}>()
</script>

<template>
    <a id="player-picture">
      <img src="/baseball.png" class="logo" alt="Player picture" />
    </a>
    <h1>Player Name {{ playerId }}</h1>
    <span>
        <p>Player Position | Bats/Throws: R/R | Height Weight | Age: ##</p>
    </span>
    <div>
        <ul>
            <li>batting stats year -3</li>
            <li>batting stats year -2</li>
            <li>batting stats year -1</li>
            <li>batting career stats</li>
        </ul>
    </div>
</template>