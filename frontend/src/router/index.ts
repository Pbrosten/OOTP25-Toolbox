import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import PlayerSearch from '@/views/PlayerSearch.vue'
import PlayerProfile from '../views/PlayerProfile.vue'

const routes = [
  { path: '/', component: LandingPage },
  { path: '/search', component: PlayerSearch },
  { path: '/players/:id', component: PlayerProfile, props: true },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
