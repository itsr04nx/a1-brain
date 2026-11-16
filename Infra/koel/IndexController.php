<?php

namespace App\Http\Controllers;

use App\Attributes\DisabledInDemo;
use App\Enums\Acl\Role;
use App\Models\User;
use App\Services\Auth\AuthenticationService;
use App\Services\UserService;
use App\Values\User\UserCreateData;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

#[DisabledInDemo]
class IndexController extends Controller
{
    public function __invoke(
        Request $request,
        UserService $userService,
        AuthenticationService $auth
    ) {
        $data = ['token' => null];

        $userLogin = $request->header('Remote-User');
        $ssoSecret = $request->header('X-SSO-Secret');

        if ($userLogin && $ssoSecret === 'koel-sso-secret-3b89f2a4c1e0d3b5') {
            $email = $request->header('Remote-Email') ?: ($userLogin . '@rohan.run.place');
            $name = $request->header('Remote-Name') ?: ucfirst($userLogin);
            $groups = $request->header('Remote-Groups', '');
            $isAdmin = ($userLogin === 'admin' || str_contains($groups, 'admins'));

            $user = User::where('email', $email)->first();
            if (!$user) {
                $user = User::where('name', $name)->orWhere('name', $userLogin)->first();
            }

            if (!$user) {
                $dto = UserCreateData::make(
                    name: $name,
                    email: $email,
                    plainTextPassword: Str::random(32),
                    role: $isAdmin ? Role::ADMIN : Role::USER,
                    avatar: null,
                    ssoId: $userLogin,
                    ssoProvider: 'Reverse Proxy'
                );
                $user = $userService->createUser($dto);
            }

            // Sync role based on admin status
            if ($isAdmin && !$user->hasRole('admin')) {
                $user->syncRoles(['admin']);
            } elseif (!$isAdmin && $user->hasRole('admin')) {
                $user->syncRoles(['user']);
            }

            // Prune old tokens older than 1 day to prevent token bloat
            $user->tokens()->where('created_at', '<', now()->subDay())->delete();

            $data['token'] = $auth->logUserIn($user)->toArray();
        }

        return view('index', $data);
    }
}
