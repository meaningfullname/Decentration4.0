import React from 'react'
import { Separator } from '../ui/separator'
import { Label } from '../ui/label'
const Header = () => {
  return (
    <header className='w-full'>
      <div className='flex flex-col w-full'>
        <Label className='text-cyan-600 text-2xl'>DeCoders</Label>
        <Separator className='my-2'/>
      </div>
    </header>
  )
}

export default Header
