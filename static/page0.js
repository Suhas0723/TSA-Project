const firebaseConfig = JSON.parse(document.getElementById('firebase_config').textContent);
console.log("maybe it fweaking worked??");
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
      })

      // Send user data to Flask backend
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
        // Send user data to Flask backend
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
              // Redirect to another page after successful login
              location.href = "/"; // Replace with your desired route
            })
            .catch((error) => {
              console.error('Error logging in on the backend:', error.message);
            });
      } else {
        alert('Please verify your email before signing in.');
      }
    })
    .catch((error) => {
      alert('Error signing in: ' + error.message);
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
document.getElementById('logout-btn').addEventListener('click', function(event) {
    event.preventDefault();  // Prevent the default action
    auth.signOut().then(() => {
        console.log("User signed out");
        window.location.href = "/signup";  // Redirect to the login page
    }).catch((error) => {
        console.error("Error signing out: ", error);
    });
});