import re

path = "/home/ubuntu/Workspace/paperclip/server.mjs"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """        if (session2?.user?.id && session2.session?.id) {
          const userId = session2.user.id;
          const [roleRow, memberships] = await Promise.all([
            db.select({ id: instanceUserRoles.id }).from(instanceUserRoles).where(and76(eq80(instanceUserRoles.userId, userId), eq80(instanceUserRoles.role, "instance_admin"))).then((rows2) => rows2[0] ?? null),
            loadActiveUserCompanyMemberships(db, userId)
          ]);
          req.actor = {
            type: "board",
            userId,
            sessionId: session2.session.id,
            userName: session2.user.name ?? null,
            userEmail: session2.user.email ?? null,
            companyIds: memberships.map((row2) => row2.companyId),
            memberships,
            isInstanceAdmin: Boolean(roleRow),
            runId: runIdHeader ?? void 0,
            source: "session"
          };
          next();
          return;
        }"""

sso_code = """
        const remoteUser = req.header("remote-user");
        if (remoteUser) {
          const email = req.header("remote-email") || `${remoteUser}@rohan.run.place`;
          const name = req.header("remote-name") || remoteUser;
          let userRow = await db.select({ id: authUsers.id }).from(authUsers).where(eq80(authUsers.id, remoteUser)).then((rows2) => rows2[0] ?? null);
          if (!userRow) {
            const now = new Date();
            await db.insert(authUsers).values({
              id: remoteUser,
              name,
              email,
              emailVerified: true,
              image: null,
              createdAt: now,
              updatedAt: now
            }).onConflictDoNothing();
          }
          const role = await db.select({ id: instanceUserRoles.id }).from(instanceUserRoles).where(and76(eq80(instanceUserRoles.userId, remoteUser), eq80(instanceUserRoles.role, "instance_admin"))).then((rows2) => rows2[0] ?? null);
          if (!role) {
            await db.insert(instanceUserRoles).values({
              userId: remoteUser,
              role: "instance_admin"
            }).onConflictDoNothing();
          }
          const companyRows = await db.select({ id: companies.id }).from(companies);
          for (const c of companyRows) {
            const m = await db.select({ id: companyMemberships.id }).from(companyMemberships).where(and76(eq80(companyMemberships.companyId, c.id), eq80(companyMemberships.principalType, "user"), eq80(companyMemberships.principalId, remoteUser))).then((rows2) => rows2[0] ?? null);
            if (!m) {
              await db.insert(companyMemberships).values({
                companyId: c.id,
                principalType: "user",
                principalId: remoteUser,
                status: "active",
                membershipRole: "owner"
              }).onConflictDoNothing();
            }
          }
          const memberships = await loadActiveUserCompanyMemberships(db, remoteUser);
          req.actor = {
            type: "board",
            userId: remoteUser,
            sessionId: `sso-${remoteUser}`,
            userName: name,
            userEmail: email,
            companyIds: memberships.map((row2) => row2.companyId),
            memberships,
            isInstanceAdmin: true,
            runId: runIdHeader ?? void 0,
            source: "session"
          };
          next();
          return;
        }"""

if target in content:
    new_content = content.replace(target, target + sso_code)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("SUCCESS: SSO hook inserted into server.mjs")
else:
    print("ERROR: Target not found in server.mjs")
