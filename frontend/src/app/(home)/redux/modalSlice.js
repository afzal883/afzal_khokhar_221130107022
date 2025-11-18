// store/modalSlice.js
import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  isOpen: false,
  component: null,
  url: null,
  modalProps: {}, // Contains the component and its props
  resolve: null, // To handle return values
};

const modalSlice = createSlice({
  name: 'modal',
  initialState,
  reducers: {
    openModal(state, action) {
      state.isOpen = true;
      state.component = action.payload.component;
      state.modalProps = action.payload.props;
      state.url = action.payload.url;
      state.resolve = action.payload.resolve; // Add resolve function
    },
    closeModal(state) {
      state.isOpen = false;
      state.component = null;
      state.modalProps = {};
      state.resolve = null;
      state.url = null;
    },
    resolveModal(state, action) {
      if (state.resolve) {
        state.resolve(action.payload); // Resolve the Promise with the payload
        state.isOpen = false;
        state.url = null;
        state.component = null;
        state.modalProps = {};
        state.resolve = null;
      }
    },
  },
});

export const { openModal, closeModal, resolveModal } = modalSlice.actions;
export const selectModal = (state) => state.modal;

export default modalSlice.reducer;
