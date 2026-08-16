import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/views/LandingPage.vue'
import PlayerSearch from '@/views/PlayerSearch.vue'
import PlayerProfile from '../views/PlayerProfile.vue'
import AdminPanel from '@/views/AdminPanel.vue'
import TeamPicker from '@/views/TeamPicker.vue'
import TeamDepthChart from '@/views/TeamDepthChart.vue'
import ProspectPipelinePicker from '@/views/ProspectPipelinePicker.vue'
import ProspectPipeline from '@/views/ProspectPipeline.vue'
import ProspectLeaderboard from '@/views/ProspectLeaderboard.vue'
import GmOrgSelect from '@/views/GmOrgSelect.vue'

const routes = [
  { path: '/', component: LandingPage },
  { path: '/gm', component: GmOrgSelect },
  { path: '/search', component: PlayerSearch },
  { path: '/players/:id', component: PlayerProfile, props: true },
  { path: '/admin', component: AdminPanel },
  { path: '/teams', component: TeamPicker },
  { path: '/teams/:id/depth-chart', component: TeamDepthChart, props: true },
  { path: '/prospects', component: ProspectPipelinePicker },
  { path: '/teams/:id/prospects', component: ProspectPipeline, props: true },
  { path: '/prospects/leaderboard', component: ProspectLeaderboard },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
