import React from 'react'
import AddressList from './AddressList'
import axios from 'axios';
import { cookies } from 'next/headers';

export const metadata = {
  alternates: {
    canonical: `https://www.hidelifestyle.co.uk/profile/addresses`,
  }
};

async function fetchAddresses() {
  const cookieStore = await cookies()
  const cookieString = cookieStore.toString()
  try {
    const response = await axios.get(`${process.env.API_URL}/getAllAddresses`,{
      withCredentials:true,
      headers:{
        "Cookie":cookieString,
        "Content-Type":"application/json"
      }
    })
    if(response.data.success){
      return response.data
    }
  } catch (error) {
    return null
  }
}

const page = async() => {
  const data = await fetchAddresses()
  console.log(data);
  
  return (
    <AddressList addresses={data?.address} />
  )
}

export default page
