"use server"

import { healthHealthGet } from '@/client';
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: App,
})

async function App() {
  const res = await healthHealthGet();
  return (
    <div className="flex w-screen justify-center">
      <p>hello, world</p>
      <p>{`${res}`}</p>
    </div>
      )
}
