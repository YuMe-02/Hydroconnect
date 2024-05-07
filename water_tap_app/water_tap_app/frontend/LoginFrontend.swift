//
//  LoginFrontend.swift
//  water_tap_app
//
//  Created by Gary Mejia on 4/18/24.
//

import Foundation
import SwiftUI


//LoginView is a parent of SignUpView
struct LoginView: View {
    @State private var email = ""
    @State private var password = ""
    @State private var isLoggedIn = false
    @State private var showError = false
    @State private var userCreationMessage = ""
    @State private var showUserCreated = false
    @State private var showUserExists = false
    @State private var jwt = ""
    @State private var response_code = 0

    var body: some View {
        if isLoggedIn {
            //user makes request to server
            HomeView(jwt_token: $jwt)
        } else {
            //try to login or make a new user
            NavigationView {
                VStack {
                    TextField("Email", text: $email)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .padding()
                        .autocapitalization(.none)
                        .onTapGesture {
                            self.email = ""
                        }
                    
                    SecureField("Password", text: $password)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .padding()
                        .autocapitalization(.none)
                        .onTapGesture {
                            self.password = ""
                        }
                    
                    // Button for logging in
                    Button(action: login)
                    {
                        Text("Login")
                            .padding()
                            .background(Color.blue)
                            .foregroundColor(.white)
                            .cornerRadius(5)
                    }
                    .padding()
                    
                    // Show error message if login fails
                    if showError {
                        Text("Incorrect username or password")
                            .foregroundColor(.red)
                            .padding()
                    }
                    // Button to navigate to SignUpView
                    NavigationLink(destination: SignUpView(showCreatedUser: $showUserCreated, showExistsUser: $showUserExists)) {
                        Text("Sign Up")
                            .padding()
                            .background(Color.green)
                            .foregroundColor(.white)
                            .cornerRadius(5)
                    }
                    .padding()
                    // Show user creation message from SignUpView
                    if showUserCreated && !showUserExists{
                        Text("User has been created!")
                            .foregroundColor(.blue)
                            .padding()
                    } else if !showUserExists && showUserExists {
                        Text("User already exists")
                            .foregroundColor(.blue)
                            .padding()
                    } else {
                        Text("")
                            .foregroundColor(.blue)
                            .padding()
                    }
                }
                .padding()
                .navigationBarTitle("Login", displayMode: .inline)
            }
        }
    }
    func login(){
        if email.isEmpty {
            print("Empty email")
            return
        }
        if password.isEmpty {
            print("Empty password")
            return
        }
        http_login_user(email: email, password: password){ response, jwt_str, error_code in DispatchQueue.main.async {
                if response == 201 {
                    isLoggedIn = true
                    jwt = jwt_str ?? ""
                }
            }
        }
    }
}

enum Route {
    case link1, link2
}

struct TestLogin: View {
var body: some View{
    NavigationStack {
       NavigationLink("Link1", value: Route.link1)
       NavigationLink("Link2", value: Route.link2)
           .navigationDestination(for: Route.self) { route in
               switch route {
               case .link1:
                   //https://sarunw.com/posts/hide-navigation-back-button-in-swiftui/
                   Link1().navigationBarBackButtonHidden(true)
               case .link2:
                   Link2()
               }
           }
       }
   }
}



struct Link1: View {
    var body: some View{
        Text("You are in Link1 view")
    }
}

struct Link2: View {
    var body: some View{
        Text("You are in Link2 view")
    }
}