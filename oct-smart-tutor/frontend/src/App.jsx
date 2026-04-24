import { useState } from 'react'
import LoginPage from './components/LoginPage'
import TrainingView from './components/TrainingView'

function App() {
  const [session, setSession] = useState(null)

  const handleLogin = (sessionData) => {
    setSession(sessionData)
  }

  const handleLogout = () => {
    setSession(null)
  }

  if (!session) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <TrainingView
      userId={session.user_id}
      sessionId={session.session_id}
      username={session.username}
      onLogout={handleLogout}
    />
  )
}

export default App
