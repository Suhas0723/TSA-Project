const firebaseConfig = JSON.parse(document.getElementById('firebase_config').textContent);
const firebaseApp = firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const firestore = firebase.firestore();
const signupForm = document.querySelector('.registration.form');
const loginForm = document.querySelector('.login.form');
const forgotForm=document.querySelector('.forgot.form');
const container=document.querySelector('.container');
const signupBtn = document.querySelector('.signupbtn');
const anchors = document.querySelectorAll('a');
signupForm.style.display = 'none';
loginForm.style.display = 'block';
forgotForm.style.display = 'none';
anchors.forEach(anchor => {
  anchor.addEventListener('click', () => {
    const id = anchor.id;
    console.log(id);
    switch(id){
    case 'loginLabel':
        signupForm.style.display = 'none';
        loginForm.style.display = 'block';
        forgotForm.style.display = 'none';
        break;
      case 'signupLabel':
        signupForm.style.display = 'block';
        loginForm.style.display = 'none';
        forgotForm.style.display = 'none';
        break;
      case 'forgotLabel':
        signupForm.style.display = 'none';
        loginForm.style.display = 'none';
        forgotForm.style.display = 'block';
        break;
    }
  });
});
signupBtn.addEventListener('click', () => {
  console.log("signup btn clicked");
  const name = document.querySelector('#name').value;
  const username = document.querySelector('#username').value;
  const email = document.querySelector('#email').value.trim();
  const password = document.querySelector('#password').value;
  const address = {
    line1: document.getElementById('line1').value,
    line2: document.getElementById('line2').value,
    city: document.getElementById('city').value,
    state: document.getElementById('state').value,
    zip: document.getElementById('zip').value,
    country: document.getElementById('country').value,
  };
  auth.createUserWithEmailAndPassword(email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      const uid = user.uid;
        user.sendEmailVerification()
        .then(() => {
          alert('Verification email sent. Please check your inbox and verify your email before signing in.');
        })
        .catch((error) => {
          alert('Error sending verification email: ' + error.message);
        });
        console.log('User data saved to Firestore');
        firestore.collection('users').doc(uid).set({
          name: name,
          username: username,
          email: email,
          address: address,
      })
      fetch('/api/create_user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          uid: uid,
          name: name,
          username: username,
          email: email,
          address: address,
        }),
      })
        .then((response) => {
          if (response.ok) {
            return response.json();
          } else {
            throw new Error('Failed to save user data to backend');
          }
        })
        .then((data) => {
          console.log('User data saved to Flask backend:', data);
        })
        .catch((error) => {
          console.error('Error saving user data to backend:', error.message);
        });

        signupForm.style.display = 'none';
        loginForm.style.display = 'block';
        forgotForm.style.display = 'none';
    })
    .catch((error) => {
      alert('Error signing up: '+error.message);
    });
});
const loginBtn = document.querySelector('.loginbtn');
loginBtn.addEventListener('click', () => {
  const email = document.querySelector('#inUsr').value.trim();
  const password = document.querySelector('#inPass').value;
  auth.signInWithEmailAndPassword(email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      if (user.emailVerified) {
        console.log('User is signed in with a verified email.');
        fetch('/api/login_user', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              uid: user.uid,
              email: user.email,
            }),
          })
            .then((response) => {
              if (response.ok) {
                return response.json();
              } else {
                throw new Error('Failed to log in on the backend');
              }
            })
            .then((data) => {
              console.log('Login data sent to Flask backend:', data);
              location.href = "/"; 
            })
            .catch((error) => {
              console.error('Error logging in on the backend:', error.message);
            });
      } else {
        alert('Please verify your email before signing in.');
      }
    })
    .catch((error) => {
      document.getElementById('wrongWarning').textContent = 'Invalid email or password.'
    });
});
const forgotBtn=document.querySelector('.forgotbtn');
forgotBtn.addEventListener('click', () => {
  const emailForReset = document.querySelector('#forgotinp').value.trim();
 if (emailForReset.length>0) {
   auth.sendPasswordResetEmail(emailForReset)
 .then(() => {
   alert('Password reset email sent. Please check your inbox to reset your password.');
        signupForm.style.display = 'none';
        loginForm.style.display = 'block';
        forgotForm.style.display = 'none';
    })
    .catch((error) => {
    alert('Error sending password reset email: ' + error.message);
  });
  }
});