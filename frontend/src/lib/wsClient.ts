class WSClient {
  socket: WebSocket | null = null

  connect(url: string){
    this.socket = new WebSocket(url)
  }
}

export default new WSClient()
