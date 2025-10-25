
// import store from '@/store'
import axios from 'axios'

const secret = localStorage.getItem('secret');
const apiKey = localStorage.getItem('apiKey');

if (secret && apiKey) {
    // Validate with backend
    axios.get('/user/secret', { params: { secret: secret } })
    .then(response => {
        console.log( response.status )
        // Login successful, update state as needed
    })
    .catch(error => {
        // Handle error, possibly treat user as new
        console.log( error.response.status )
    });
}
