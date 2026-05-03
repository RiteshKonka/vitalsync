import create from 'zustand'

type State = {
  agents: Record<string, any>
}

export const useAgentStore = create<State>(()=>({
  agents: {}
}))
