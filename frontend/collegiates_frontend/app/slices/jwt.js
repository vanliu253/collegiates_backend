import { createSlice } from '@reduxjs/toolkit'

export const jwtSlice = createSlice({
  name: 'jwt',
  initialState: {
    refesh:"",
    access:""
  },
  reducers: {
    clear: state => {
      // Redux Toolkit allows us to write "mutating" logic in reducers. It
      // doesn't actually mutate the state because it uses the Immer library,
      // which detects changes to a "draft state" and produces a brand new
      // immutable state based off those changes
      state = {
        refesh:"",
        access:""
      }
    },
    set: (jsonBody) => {
      state = jsonBody
    },
    update: (newAccess) => {
      state.access = newAccess
    }
  }
})

// Action creators are generated for each case reducer function
export const { clear, set, update } = jwtSlice.actions

export default jwtSlice.reducer