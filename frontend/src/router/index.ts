import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import PlayerDetails from '@/components/PlayerDetails.vue'

const routes = [
  { path: '/', component: LandingPage },
  { path: '/players/:id', component: PlayerDetails }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
